# PythonAgendaBuilder
Vibe coded python module to build a latex agenda. It supports rendering either with `tikz` or with `tabular`. Main file can be used to create an Agenda by parsing a csv file with events. Running without any arguments provided will output the LaTeX Code [LaTeX code](example/tex/example_tikz.tex) for the [Example Agenda](example/pdf/example_tikz.pdf).

If one does not want to use the 'tikz' package one can use the `--legacy` option. To save the output directly to a file use `--file <filename>`. One can parse the agenda events from a csv file by using `--csv-file`. There are numerous other options you can explore with `--help`. You can use `--day-str-format "%A"` to show the full weekday name without date in the header row as in [example/pdf/test_tikz.pdf].

A csv file with the following columns is expected `EVENT_TITLE,EVENT_START,EVENT_END,EVENT_TEXT,EVENT_TEXT_SIZE,EVENT_ID,EVENT_COLOR,IS_OPEN_ENDED,IS_SPECIAL`. If no header is provided, the order must be as specified. `EVENT_COLOR` can be a hex value or a color_id (automatically picks a color from a palette) which allows assigning the same color to multiple events. See also [example/csv/my_agenda.csv](example/csv/my_agenda.csv) for reference.


Image of Example PDF with tikz rendering:

![Image of Example PDF with tikz rendering](example/png/example_tikz.png)


Image of Example PDF with table rendering:

![Image of Example PDF with table rendering](example/png/example_table.png)
