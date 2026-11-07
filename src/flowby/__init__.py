"""flowby: the graph under the board.

the modules, in the order a change travels through them:

    dtypes    the four wires, and the refusal to add a fifth
    graph     nodes, typed ports, wires, topological order, cycles
    presets   the subgraphs a slider stands in for
    scene     elements on a board, which are nodes with a position
    compile   the plan a shell script can run, flattened once
    routes    where it runs, and what each place honestly cannot do
    job       a plan's life, its illegal moves, and its artifacts
    hub       the fan-out to the boards that are open

nothing above imports a web framework. `app/` is the binding, not the model.
"""

__version__ = "0.1.0"
__all__ = ["dtypes", "graph", "presets", "scene", "compile", "routes", "job", "hub"]
