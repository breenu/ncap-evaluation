// Typst styling for the Phase 10 documents (DEC-206). Figures carry their own numbers ("Figure 4.")
// in the image and the caption, so Typst's automatic "Figure N:" prefix is switched off.
#set figure(numbering: none)
#show figure.caption: set align(left)
#show figure.caption: set text(size: 8.5pt)
#show table: set text(size: 8pt)
#set table(inset: 4pt)
// No creation date in the PDF metadata, so the PDFs rebuild byte for byte (DEC-211).
#set document(date: none)
