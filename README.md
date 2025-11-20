# PythonAgendaBuilder
Vibe coded python module to build a latex agenda. It supports rendering either with `tikz` or with `tabular`.

Running the example main file outputs the [LaTeX code](example/example_tikz.tex) for the [pdf](example/example_tikz.pdf) of the agenda:

![Image of Example PDF with tikz rendering](example/example_tikz.png)

Alternatively if one does not want to use the 'tikz' package one can use the `--legacy` option. To save the output directly to a file use `--file <filename>`.


![Image of Example PDF with table rendering](example/example_table.png)