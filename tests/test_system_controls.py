from afilmbykirk.system_controls import _split_nmcli


def test_nmcli_fields_preserve_escaped_colons():
    assert _split_nmcli(r"*:Kirk\: Home:92:WPA2") == [
        "*", "Kirk: Home", "92", "WPA2"
    ]
