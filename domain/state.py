from collections import defaultdict, deque
from typing import Deque, Dict, List
from services.config import MAX_HISTORY

History = Deque[dict]  # {"role": "...", "content": "..."}
chats: Dict[int, History] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
carts = defaultdict(lambda: defaultdict(int))  # chat_id -> {pid: qty}
