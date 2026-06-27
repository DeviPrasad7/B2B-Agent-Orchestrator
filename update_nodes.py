import glob
import re

for file_path in glob.glob('c:/Ideal-Customer-Profile-Agent/src/agent/agents/*.py'):
    if file_path.endswith('__init__.py'):
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Import modifications
    content = content.replace("from ..utils import Toolbox, MemoryStore", "from ..utils import Toolbox\nfrom services.memory_service import MemoryService")
    content = content.replace("from ..utils import Toolbox, CircuitBreakerState, MemoryStore", "from ..utils import Toolbox, CircuitBreakerState\nfrom services.memory_service import MemoryService")
    content = content.replace("from ..utils import Toolbox, MemoryStore, MonitoringService", "from ..utils import Toolbox, MonitoringService\nfrom services.memory_service import MemoryService")
    content = content.replace("from ..utils import Toolbox, CircuitBreakerState, MonitoringService, MemoryStore", "from ..utils import Toolbox, CircuitBreakerState, MonitoringService\nfrom services.memory_service import MemoryService")
    content = content.replace("from ..utils import Toolbox, CircuitBreakerState, MemoryStore, MonitoringService", "from ..utils import Toolbox, CircuitBreakerState, MonitoringService\nfrom services.memory_service import MemoryService")

    # Type hint modification
    content = content.replace("memory: MemoryStore", "memory: MemoryService")

    # Await modifications
    content = re.sub(r'([ \t]+)(memory\.(?:mark_event_processed|save_prospect_state|rollback_prospect_state))', r'\1await \2', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Nodes updated.")
