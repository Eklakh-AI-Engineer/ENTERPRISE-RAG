import pytest

from app.persistence.entities import MessageRecord
from app.persistence.in_memory import InMemoryAnswerRepository, InMemoryConversationRepository
from app.query.services import AnswerPersistenceService, ConversationService, QueryValidationError


def test_conversation_is_owner_scoped():
    repo = InMemoryConversationRepository()
    service = ConversationService(repo)
    conversation = service.create(organization_id="org-a", user_id="user-a")
    message = service.add_user_message(
        conversation_id=conversation.id, user_id="user-a", content="Where is the policy?"
    )
    assert message.user_id == "user-a"
    with pytest.raises(KeyError):
        service.get(conversation_id=conversation.id, user_id="user-b")


def test_answer_persistence_links_to_query_message():
    conversations = InMemoryConversationRepository()
    answers = InMemoryAnswerRepository()
    conversation = ConversationService(conversations).create(organization_id="org-a", user_id="user-a")
    message = ConversationService(conversations).add_user_message(
        conversation_id=conversation.id, user_id="user-a", content="Question"
    )
    answer = AnswerPersistenceService(answers).save_turn(
        message=message, query_text="Question", answer_text="Grounded answer", retrieval_mode="hybrid"
    )
    assert answer.message_id == message.id
    assert answers.answers[answer.id] is answer


def test_answer_requires_user_message():
    message = MessageRecord(id="m", conversation_id="c", user_id="u", role="assistant", content="x")
    with pytest.raises(QueryValidationError):
        AnswerPersistenceService(InMemoryAnswerRepository()).save_turn(
            message=message, query_text="q", answer_text="a", retrieval_mode="dense"
        )
