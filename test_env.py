import sys
import os

print(f"Interpretador Python: {sys.executable}")
print(f"Versão do Python: {sys.version}")
print(f"Caminho atual do projeto: {os.getcwd()}")

# Teste se o arquivo principal do projeto existe (por exemplo, main.py)
main_py_path = os.path.join(os.getcwd(), 'main.py')
if os.path.exists(main_py_path):
    print(f"Arquivo 'main.py' encontrado em: {main_py_path}")
else:
    print(f"Arquivo 'main.py' NÃO encontrado em: {main_py_path}")