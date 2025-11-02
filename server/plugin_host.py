import queue
import threading
import os, time, importlib, inspect, hashlib
from types import ModuleType
import traceback
import logging


class PluginHost:
    def __init__(self, plugin_dir="plugins", poll_interval=2.0):
        self.plugin_dir = plugin_dir
        self.poll_interval = poll_interval
        self.plugins = {}
        self.module_hashes = {}
        self._listeners = {}

        self._queue = queue.Queue()
        self._watcher_thread = None
        self._stop_event = threading.Event()

    def start(self):
        logging.info("[HotReloadingModule 🔥] Starting plugin host...")
        self.load_all()
        try:
            while True:
                self.check_for_changes()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logging.info("\n[HotReloadingModule 🔥] Shutting down...")
            self.unload_all()

    def _calc_hash(self, path):
        if not os.path.exists(path):
            logging.warning(f"[HotReloadingModule 🔥] Tried to load plugin with invalid path={path}")
            return None
        sha = hashlib.sha256()

        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in sorted(files):
                    if f.endswith(".py"):
                        full = os.path.join(root, f)
                        with open(full, "rb") as fp:
                            sha.update(fp.read())
        else:
            with open(path, "rb") as fp:
                sha.update(fp.read())

        return sha.hexdigest()

    def discover(self):
        entries = []
        for entry in os.listdir(self.plugin_dir):
            if entry.startswith("_"):
                continue
            full_path = os.path.join(self.plugin_dir, entry)
            
            logging.debug(f"[HotReloadingModule 🔥] Found plugin candidate {full_path}")

            if entry.endswith(".py"):
                entries.append(entry)

            elif os.path.isdir(full_path) and os.path.isfile(os.path.join(full_path, "__init__.py")):
                entries.append(entry)

        return entries

    def load_all(self):
        for name in self.discover():
            self.load_plugin(name)

    def load_plugin(self, name):
        modname = f"{self.plugin_dir.removeprefix('./')}.{name.removesuffix('.py')}"
        path = os.path.join(self.plugin_dir, name)
        hash_ = self._calc_hash(path)

        if name in self.plugins and self.plugins[name][2] == hash_:
            return
        
        if name in self.plugins:
            self.reload_plugin(name)
            return

        try:
            logging.info(f"[HotReloadingModule 🔥] Loading plugin: {name}")
            module = importlib.import_module(modname)

            plugin_cls = getattr(module, "Plugin", None)
            if plugin_cls is None:
                logging.warning(f"[HotReloadingModule 🔥] ⚠️  Plugin {name} has no 'Plugin' class, skipping.")
                return

            instance = plugin_cls(self)
            instance.register()

            self.plugins[name] = (module, instance, hash_)
            logging.info(f"[HotReloadingModule 🔥] ✅ Registered plugin: {name}")

        except Exception:
            logging.info(f"[HotReloadingModule 🔥] ❌ Failed to load plugin '{name}'")
            traceback.print_exc()

    def unload_plugin(self, name):
        if name not in self.plugins:
            return
        module, instance, _ = self.plugins.pop(name)
        try:
            instance.deregister()
            logging.info(f"[HotReloadingModule 🔥] 🧹 Unloaded plugin: {name}")
        except Exception:
            logging.warning(f"[HotReloadingModule 🔥] ⚠️ Error during unload of {name}")

    def reload_plugin(self, name):
        if name not in self.plugins:
            return self.load_plugin(name)

        module, instance, old_hash = self.plugins[name]
        path = os.path.join(self.plugin_dir, name)
        new_hash = self._calc_hash(path)

        if new_hash == old_hash:
            return
        
        logging.info(f"[HotReloadingModule 🔥] 🔄 Reloading plugin: {name}")
        try:
            instance.deregister()
        except Exception:
            logging.error(f"[HotReloadingModule 🔥] ⚠️  Error during deregistration of {name}")
            traceback.print_exc()

        try:
            importlib.reload(module)
            plugin_cls = getattr(module, "Plugin", None)
            if plugin_cls is None:
                logging.info(f"[HotReloadingModule 🔥] ⚠️  Plugin {name} has no 'Plugin' class after reload.")
                del self.plugins[name]
                return

            instance = plugin_cls(self)
            instance.register()

            self.plugins[name] = (module, instance, new_hash)
            logging.info(f"[HotReloadingModule 🔥] ✅ Reloaded plugin: {name}")

        except Exception:
            logging.info(f"[HotReloadingModule 🔥] ❌ Failed to reload plugin '{name}'")
            traceback.print_exc()

    def _instantiate(self, module: ModuleType):
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if hasattr(cls, "register") and hasattr(cls, "deregister") and hasattr(cls, "get_type"):
                instance = cls(self)
                instance.register()
                return instance
        return None

    def unload_all(self):
        for name in list(self.plugins.keys()):
            self.unload_plugin(name)

    def check_for_changes(self):
        discovered = set(self.discover())
        loaded = set(self.plugins.keys())

        for name in discovered - loaded:
            self.load_plugin(name)

        for name in loaded - discovered:
            logging.info(f"[HotReloadingModule 🔥] Unloading removed plugin: {name}")
            self.unload_plugin(name)

        for name in discovered & loaded:
            path = os.path.join(self.plugin_dir, f"{name}.py")
            new_hash = self._calc_hash(path)
            if new_hash != self.module_hashes.get(name):
                self.reload_plugin(name)

    def add_event_listener(self, event, callback):
        self._listeners.setdefault(event, []).append(callback)

    def emit_event(self, event, *args, **kwargs):
        for cb in self._listeners.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                logging.info(f"[HotReloadingModule 🔥] Error in handler '{event}': {e}")

    def _watch_for_changes(self):
        last_seen = {}

        while not self._stop_event.is_set():
            for name in self.discover():
                path = os.path.join(self.plugin_dir, name)
                hash_ = self._calc_hash(path)

                if not hash_:
                    logging.debug(f"[HotReloadingModule 🔥] Failed to hash plugin {path}")
                    continue

                logging.debug(f"[HotReloadingModule 🔥] Successfully generated hash for plugin {path}={hash_}")

                old_hash = last_seen.get(name)
                last_seen[name] = hash_

                if old_hash is None and name not in self.plugins:
                    self._queue.put(("load", name))
                elif old_hash != hash_:
                    self._queue.put(("reload", name))

            for name in list(last_seen.keys()):
                path = os.path.join(self.plugin_dir, name)
                if not os.path.exists(path):
                    last_seen.pop(name)
                    self._queue.put(("unload", name))


            logging.debug("[HotReloadingModule 🔥] Fired watch event loop")
            time.sleep(self.poll_interval)
        
    def start_watcher(self):
        if self._watcher_thread and self._watcher_thread.is_alive():
            return
        self._stop_event.clear()
        self._watcher_thread = threading.Thread(target=self._watch_for_changes, daemon=True)
        self._watcher_thread.start()
        logging.info("[HotReloadingModule 🔥] 🔍 Plugin watcher started.")

    def stop_watcher(self):
        if not self._watcher_thread:
            return
        self._stop_event.set()
        self._watcher_thread.join(timeout=3)
        logging.info("[HotReloadingModule 🔥] 🛑 Plugin watcher stopped.")

    def process_plugin_events(self):
        try:
            while True:
                action, name = self._queue.get_nowait()
                if action == "load":
                    self.load_plugin(name)
                elif action == "reload":
                    self.reload_plugin(name)
                elif action == "unload":
                    self.unload_plugin(name)
                else:
                    logging.info(f"[HotReloadingModule 🔥] ⚠️ Unknown plugin action: {action}")
        except queue.Empty:
            pass


    def __type_schema_check(self, type, classobj):
        if type == "MODEL":
            if hasattr(classobj, "predict_next") and hasattr(classobj, "get_formatted_name"):
                return True
            else: return False

        return True

    def get_all_plugins(self, type: str = None):
        if type:

            typed_plugins = []
            candidates = [self.plugins[plugin][1] for plugin in self.plugins if self.plugins[plugin][1].get_type() == type]

            for candidate in candidates:
                if self.__type_schema_check(type, candidate):
                    typed_plugins.append(candidate)
                else:
                    logging.warning(f"[HotReloadingModule 🔥] ⚠️ Plugin: {candidate} is malformed")
            return typed_plugins
        else:
            return self.plugins

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    host = PluginHost("./plugins")
    host.start_watcher()

    try:
        while True:
            host.process_plugin_events()
            time.sleep(0.5)
    except KeyboardInterrupt:
        host.stop_watcher()

