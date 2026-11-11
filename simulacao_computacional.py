"""Entrada da simulação energética."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from analise_simulacao import executar
if __name__ == "__main__":
    executar(verbose=True)
