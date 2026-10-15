"""Serialize full SEC verification, then reuse only byte-identical projections."""
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
import re
from threading import RLock

from .sec_views import SecViews, PATTERN
from .workspace import contained, read_json, sha256

METHOD_SHA = sha256(Path(__file__))


class VerifiedSecReadCache(SecViews):
    """Every request hashes the full graph;first load uses the original verifier."""
    def __init__(self, backend):
        self.backend = backend
        self.root = backend.root
        self.methods = backend.methods
        self._lock = RLock()
        self._cached = OrderedDict()

    def _input_pins(self, identifier):
        if not isinstance(identifier,str) or not PATTERN.fullmatch(identifier):
            raise ValueError('Invalid SEC view identifier')
        if sha256(Path(__file__)) != METHOD_SHA:
            raise ValueError('SEC cache method changed;restart required')
        folder = contained(self.root,'artifacts/private/'+identifier)
        anchor = read_json(folder/'view-complete.json')
        case_id = anchor['case_id']
        if not isinstance(case_id,str) or not re.fullmatch(r'sec-case-[0-9a-f]{12}',case_id):
            raise ValueError('Invalid SEC canonical case binding')
        case = contained(self.root,'artifacts/private/'+case_id)
        receipt = read_json(case/'case-complete.json')
        source_id = receipt['source_id']
        if not isinstance(source_id,str) or not re.fullmatch(r'sec-source-[0-9a-f]{12}',source_id):
            raise ValueError('Invalid SEC source binding')
        source = contained(self.root,'data/private/sec/'+source_id)
        acquisition = read_json(source/'acquisition-complete.json')
        pins = {}
        def pin(path, expected=None):
            digest = sha256(path)
            if expected is not None and digest != expected:
                raise ValueError('SEC evidence bytes changed')
            pins[str(path)] = digest
        pin(folder/'view-complete.json')
        pin(folder/'snapshot.json',anchor['snapshot_sha256'])
        pin(case/'case-complete.json',anchor['case_receipt_sha256'])
        pin(source/'acquisition-complete.json',receipt['source_receipt_sha256'])
        for name,digest in receipt['files'].items():pin(contained(case,name),digest)
        for s in acquisition['files']:pin(contained(source,s['file']),s['sha256'])
        # Loaded verifier methods and their receipt bindings remain mandatory.
        for bundle in [anchor['methods'],receipt['methods'],acquisition['methods']]:
            for name,digest in bundle.items():
                if not re.fullmatch(r'[a-z_]+',name):raise ValueError('Invalid SEC method name')
                pin(Path(__file__).with_name(name+'.py'),digest)
        return pins

    def view(self, identifier):
        with self._lock:
            pins = self._input_pins(identifier)
            if identifier in self._cached:
                previous,snapshot = self._cached[identifier]
                if previous != pins:
                    raise ValueError('SEC verification graph changed;cached view rejected')
                self._cached.move_to_end(identifier)
                return deepcopy(snapshot)
            snapshot = self.backend.view(identifier)
            if self._input_pins(identifier) != pins:
                raise ValueError('SEC evidence changed during full verification')
            self._cached[identifier] = (pins,deepcopy(snapshot))
            if len(self._cached) > 8:self._cached.popitem(last=False)
            return deepcopy(snapshot)
