from unittest.mock import patch, MagicMock, mock_open
from app import get_file_status_symbol, get_dependencies, genuml, main

def test_get_file_status_symbol():
    assert get_file_status_symbol("added") == "+"
    assert get_file_status_symbol("removed") == "-"
    assert get_file_status_symbol("modified") == "~"
    assert get_file_status_symbol("renamed") == "@"
    assert get_file_status_symbol("unknown") == "unknown"

@patch("app.Session.get")
def test_get_dependencies(get_req_mock):

    get_req_mock.side_effect = [
        MagicMock(status_code=200, json=lambda: [{"name": "v1.0", "commit": {"sha": "1234"}}]),
        MagicMock(status_code=200, json=lambda: [
            {"sha": "5678", "commit": {"message": "Test commit"}, "parents": [{"sha": "1234"}]}
        ]),
        MagicMock(status_code=200, json=lambda: {"files": [{"status": "added", "filename": "file1.txt"}]})
    ]

    repo_url = "https://github.com/user/repo"
    tag = "v1.0"
    result = get_dependencies(repo_url, tag, depth=10, token="dummy_token")

    assert result == [
        {
            "sha": "5678",
            "message": "Test commit",
            "parents": [{"sha": "1234"}],
            "files": ["+ /file1.txt"]
        }
    ]

    assert get_req_mock.call_count == 3

def test_genuml():
    commits = [
        {
            "sha": "5678",
            "message": "Test commit",
            "parents": [{"sha": "1234"}],
            "files": ["+ /file1.txt"]
        }
    ]
    result = genuml("v1.0", commits)
    assert "@startuml" in result
    assert "node \"v1.0\" as repo" in result
    assert "card 5678 [" in result
    assert "+ /file1.txt" in result
    assert "1234 --> 5678" in result
    assert "@enduml" in result

@patch("app.open", new_callable=mock_open, read_data="token: dummy_token\nrepo: https://github.com/user/repo\ntag: v1.0\n")
@patch("app.get_dependencies")
@patch("app.Popen")
@patch("os.mkdir")
@patch("os.path.exists", return_value=False)
def test_main(mock_exists, mock_mkdir, mock_popen, mock_get_dependencies, mock_open_file):
    mock_get_dependencies.return_value = [
        {
            "sha": "5678",
            "message": "Test commit",
            "parents": [{"sha": "1234"}],
            "files": ["+ /file1.txt"]
        }
    ]
    mock_popen.return_value.wait = MagicMock()

    main()

    mock_mkdir.assert_called_once_with("out")
    mock_open_file.assert_called_with("out/repo@v1.0.puml", "w")
    mock_open_file().write.assert_called_once()
    mock_popen.assert_not_called()