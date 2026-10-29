"""Fictional document metadata and substantive policy sections."""

from uuid import UUID

import pytest


TENANT = '10000000-0000-0000-0000-000000000001'
ACTOR = '20000000-0000-0000-0000-000000000001'
SOURCE = '30000000-0000-0000-0000-000000000001'
DOCUMENT = '40000000-0000-0000-0000-000000000001'
VERSION = '50000000-0000-0000-0000-000000000001'
RUN = '60000000-0000-0000-0000-000000000001'


def row(number, section, text, **extra):
    return {
        'chunk_id': str(UUID(int=number)), 'document_id': DOCUMENT,
        'document_version_id': VERSION, 'processing_run_id': RUN,
        'chunk_sequence': number, 'section_title': section,
        'content_text': text, 'distance': 0.2 + number / 100,
        **extra,
    }


@pytest.fixture
def metadata_rows():
    return [
        row(1, '19. Suggested Retrieval Metadata', 'Document metadata; authority_status: draft_sample_not_official.'),
        row(2, 'HOSTEL RULES', 'Document type: Sample policy. Version: 1.0. '
            'This is a draft sample, not an officially approved college policy.'),
        row(3, '1. Purpose and Scope', 'Residents must follow the hostel rules.'),
        row(4, None, 'HOSTEL POLICY Draft sample for testing Page 1'),
    ]


@pytest.fixture
def policy_rows():
    return [
        row(5, '2. Rooms', 'Residents must obtain permission before changing rooms.'),
        row(6, '5. Visitors', 'Overnight guests need approval from the hostel office.'),
        row(7, '6. Quiet hours', 'The sample quiet hours are illustrative, not verified college timings.'),
    ]
