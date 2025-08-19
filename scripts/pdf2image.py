import pypdfium2 as pdfium
import pathlib

path = pathlib.Path("./sensitive")
print(path.absolute())
files = []

for file in path.glob("*.pdf"):
    if file.is_file():
        files.append(file)

for file in files:
    print(file)
    # Load a document
    pdf = pdfium.PdfDocument(file)

    # Loop over pages and render
    for i in range(len(pdf)):
        page = pdf[i]
        image = page.render(scale=4).to_pil()
        image.save(f"./sensitive/output_{file.name}_{i:03d}.png")
