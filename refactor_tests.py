import sys

with open('tests/test_smart_reply.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('assert args[2] == "question"             # intent', 'assert args[2].intent == "question"             # intent')

with open('tests/test_smart_reply.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
