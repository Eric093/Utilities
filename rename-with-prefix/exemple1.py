import re

nom = "doc_RAG.txt"

nouveau = re.sub(r'^(?!AI_)(.*RAG.*)$', r'AI_\1', nom)

print(nouveau)