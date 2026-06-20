from __future__ import annotations

import json

from validacao_final_v2 import executar


if __name__ == "__main__":
    print(json.dumps(executar(), ensure_ascii=False, indent=2))
