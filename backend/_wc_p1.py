"""Write the corrected public_chat.py file."""

def w(path, content):
    with open(path, 'w') as f:
        f.write(content)

import os
os.chdir('F:\\Git Project\\CollegeAIChatbot\\backend')

content = (
    '"""Phase 6.13 - Public (unauthenticated) chat endpoint service.\n'
    '\n'
    'Mirrors app.services.chat.process_chat_request so that public conversations\n'
    'reuse the same chat boundary, turn/conversation ownership model, bounded\n'
    'history, query rewriting, retrieval, generation, and citation pipeline -\n'
    'EXCEPT:\n'
    '\n'
    '1. user_id is always PUBLIC_USER_ID (a constant, never derived from a JWT).\n'
    '2. Personalization is never loaded (no current_user -> no student context).\n'
    '3. institution_id is accepted for forward-compatibility but does not\n'
    '   participate in any tenant-scoped authorization check.\n'
    '"""\n'
)

w('app/services/public_chat.py', content)
print('Part 1 done')
