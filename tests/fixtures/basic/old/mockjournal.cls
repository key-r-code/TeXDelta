\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{mockjournal}[2026/01/01 Synthetic TeXDelta fixture]
\LoadClass{article}
\RequirePackage{environ}
\newcommand\storedabstract{}
\RenewEnviron{abstract}{\global\let\storedabstract\BODY}
\renewcommand\maketitle{\begin{center}{\LARGE\bfseries\@title\par}\end{center}\storedabstract\par\medskip}
\endinput
