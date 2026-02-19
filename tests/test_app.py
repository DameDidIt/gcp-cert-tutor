import pytest
from unittest.mock import patch
from gcp_tutor.app import SessionExitRequested, session_prompt, session_int_prompt


def test_session_exit_requested_is_exception():
    with pytest.raises(SessionExitRequested):
        raise SessionExitRequested()


def test_session_prompt_raises_on_q():
    with patch("gcp_tutor.app.Prompt.ask", return_value="q"):
        with pytest.raises(SessionExitRequested):
            session_prompt("test prompt")


def test_session_prompt_raises_on_menu():
    with patch("gcp_tutor.app.Prompt.ask", return_value="menu"):
        with pytest.raises(SessionExitRequested):
            session_prompt("test prompt")


def test_session_prompt_returns_normal_input():
    with patch("gcp_tutor.app.Prompt.ask", return_value="hello"):
        result = session_prompt("test prompt")
        assert result == "hello"


def test_session_int_prompt_raises_on_q():
    with patch("gcp_tutor.app.Prompt.ask", return_value="q"):
        with pytest.raises(SessionExitRequested):
            session_int_prompt("rate", choices=["0","1","2","3","4","5"])


def test_session_int_prompt_returns_normal_input():
    with patch("gcp_tutor.app.Prompt.ask", return_value="3"):
        result = session_int_prompt("rate", choices=["0","1","2","3","4","5"])
        assert result == 3
