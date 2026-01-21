#define _GNU_SOURCE 1
#include <Python.h>
#include <linux/futex.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include <time.h>
#include <stdatomic.h>
#include <stdbool.h>

// (Written by AI)

// ---------------------------------------------------------------------
// Futex helpers
// ---------------------------------------------------------------------

static inline int futex_wait(uint32_t *addr, uint32_t expected, const struct timespec *timeout) {
    return syscall(SYS_futex, addr, FUTEX_WAIT, expected, timeout, NULL, 0);
}

static inline int futex_wake(uint32_t *addr, int n) {
    return syscall(SYS_futex, addr, FUTEX_WAKE, n, NULL, NULL, 0);
}

#if defined(__x86_64__) || defined(__i386__)
#define CPU_RELAX() __asm__ __volatile__("pause")
#elif defined(__aarch64__)
#define CPU_RELAX() __asm__ __volatile__("yield")
#else
#define CPU_RELAX() do { } while (0)
#endif

// ---------------------------------------------------------------------
// FutexWord type
// ---------------------------------------------------------------------

typedef struct {
    PyObject_HEAD
    uint32_t *uaddr;
    PyObject *owner;  // reference to original buffer
} FutexWordObject;

static int FutexWord_init(FutexWordObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"buffer", NULL};
    PyObject *buf_obj = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O", kwlist, &buf_obj)) {
        return -1;
    }

    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) < 0) {
        return -1;
    }

    if (view.len < 4 || ((uintptr_t)view.buf % 4) != 0) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "need 4-byte aligned >=4 buffer");
        return -1;
    }

    self->uaddr = (uint32_t *)view.buf;
    self->owner = buf_obj;
    Py_INCREF(self->owner);
    PyBuffer_Release(&view);
    return 0;
}

static void FutexWord_dealloc(FutexWordObject *self) {
    Py_XDECREF(self->owner);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *FutexWord_load(FutexWordObject *self, PyObject *Py_UNUSED(ignored)) {
    uint32_t val = __atomic_load_n(self->uaddr, __ATOMIC_ACQUIRE);
    return PyLong_FromUnsignedLong(val);
}

static PyObject *FutexWord_store(FutexWordObject *self, PyObject *args) {
    unsigned long value;
    if (!PyArg_ParseTuple(args, "k", &value)) {
        return NULL;
    }
    __atomic_store_n(self->uaddr, (uint32_t)value, __ATOMIC_RELEASE);
    Py_RETURN_NONE;
}

static PyObject *FutexWord_wake(FutexWordObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"n", NULL};
    int n = 1;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|i", kwlist, &n)) {
        return NULL;
    }
    if (n <= 0) {
        n = 1;
    }
    int res = futex_wake(self->uaddr, n);
    if (res < 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    return PyLong_FromLong(res);
}

// wait_for_value(desired: int, timeout_ns: int = -1) -> bool
static PyObject *FutexWord_wait_for_value(FutexWordObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"desired", "timeout_ns", NULL};
    unsigned long desired_ul;
    long timeout_ns = -1;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "k|l", kwlist, &desired_ul, &timeout_ns)) {
        return NULL;
    }
    uint32_t desired = (uint32_t)desired_ul;

    uint32_t cur = __atomic_load_n(self->uaddr, __ATOMIC_ACQUIRE);
    if (cur == desired) {
        Py_RETURN_TRUE;
    }

    // Small spin first (entirely in C, no Python busy wait)
    const int SPIN_LIMIT = 200;
    for (int i = 0; i < SPIN_LIMIT; i++) {
        CPU_RELAX();
        cur = __atomic_load_n(self->uaddr, __ATOMIC_RELAXED);
        if (cur == desired) {
            Py_RETURN_TRUE;
        }
    }

    struct timespec ts;
    struct timespec *tsp = NULL;
    if (timeout_ns >= 0) {
        ts.tv_sec = timeout_ns / 1000000000L;
        ts.tv_nsec = timeout_ns % 1000000000L;
        tsp = &ts;
    }

    while (1) {
        cur = __atomic_load_n(self->uaddr, __ATOMIC_ACQUIRE);
        if (cur == desired) {
            Py_RETURN_TRUE;
        }

        int err = futex_wait(self->uaddr, cur, tsp);
        if (err == 0) {
            // woken; loop to re-check
            continue;
        }
        if (errno == ETIMEDOUT) {
            Py_RETURN_FALSE;
        }
        if (errno == EAGAIN) {
            // value changed between load and futex_wait; re-check
            continue;
        }
//        if (errno == EINTR) {
//            // interrupted by signal; retry
//            continue;
//        }
        return PyErr_SetFromErrno(PyExc_OSError);
    }
}

static PyMethodDef FutexWord_methods[] = {
    {"load", (PyCFunction)FutexWord_load, METH_NOARGS, PyDoc_STR("Load current value (acquire)")},
    {"store", (PyCFunction)FutexWord_store, METH_VARARGS, PyDoc_STR("Store value (release)")},
    {"wake", (PyCFunction)FutexWord_wake, METH_VARARGS | METH_KEYWORDS,
     PyDoc_STR("Wake up to n waiters; returns number of threads woken")},
    {"wait_for_value", (PyCFunction)FutexWord_wait_for_value, METH_VARARGS | METH_KEYWORDS,
     PyDoc_STR("Block until value == desired, optional timeout_ns; returns bool")},
    {NULL, NULL, 0, NULL},
};

static PyTypeObject FutexWordType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "shm_rpc_bridge._internal.linux_futex.FutexWord",
    .tp_basicsize = sizeof(FutexWordObject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "Futex-backed word bound to a 4-byte buffer",
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)FutexWord_init,
    .tp_dealloc = (destructor)FutexWord_dealloc,
    .tp_methods = FutexWord_methods,
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    .m_name = "shm_rpc_bridge._internal.linux_futex",
    .m_doc = "Linux futex-backed synchronization primitives for shm-rpc-bridge",
    .m_size = -1,
};

PyMODINIT_FUNC PyInit_linux_futex(void) {
    PyObject *m;
    if (PyType_Ready(&FutexWordType) < 0)
        return NULL;

    m = PyModule_Create(&moduledef);
    if (m == NULL)
        return NULL;

    Py_INCREF(&FutexWordType);
    if (PyModule_AddObject(m, "FutexWord", (PyObject *)&FutexWordType) < 0) {
        Py_DECREF(&FutexWordType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}