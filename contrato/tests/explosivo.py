
"""Módulo que falla al importarse.

Permite comprobar que listar() no ejecuta código de los complementos.
"""

raise RuntimeError("este módulo no debe importarse al listar complementos")
