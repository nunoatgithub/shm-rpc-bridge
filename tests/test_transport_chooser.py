import importlib
import os

import pytest


class TestTransportChooser:
    def test_transport_chooser_raises_on_unknown_os(self, monkeypatch):
        monkeypatch.setattr(os, "name", "alien_os")

        import shm_rpc_bridge.transport.transport_chooser as transport_chooser

        with pytest.raises(Exception):
            importlib.reload(transport_chooser)
