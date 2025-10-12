# path: src/utils/threadsafe_pickle_queue.py
import pickle
from pathlib import Path
import threading
from typing import Any, List

_pickle_queue_lock = threading.Lock()

def add_to_pickle_queue(item: Any, path: Path) -> None:
    """
    Ajoute un item à une queue stockée en pickle de façon thread-safe.
    Fusionne automatiquement avec le contenu existant.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with _pickle_queue_lock:
        # Charger la queue existante si elle existe
        if path.exists():
            with open(path, "rb") as f:
                queue: List[Any] = pickle.load(f)
        else:
            queue = []

        # Ajouter l’élément et sauvegarder
        queue.append(item)
        with open(path, "wb") as f:
            pickle.dump(queue, f, protocol=pickle.HIGHEST_PROTOCOL)

def load_pickle_queue(path: Path) -> List[Any]:
    """
    Charge la queue pickle de façon thread-safe.
    """
    with _pickle_queue_lock:
        if not path.exists():
            return []
        with open(path, "rb") as f:
            return pickle.load(f)

def clear_pickle_queue(path: Path) -> None:
    """
    Vide la queue pickle.
    """
    with _pickle_queue_lock:
        if path.exists():
            with open(path, "wb") as f:
                pickle.dump([], f, protocol=pickle.HIGHEST_PROTOCOL)
