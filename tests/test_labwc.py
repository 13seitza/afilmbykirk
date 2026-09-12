from scripts.configure_labwc import main


def test_adds_cursor_keybind_without_replacing_existing_config(tmp_path, monkeypatch):
    config = tmp_path / "rc.xml"
    config.write_text(
        "<labwc_config><keyboard><keybind key=\"A-F4\" /></keyboard></labwc_config>"
    )
    monkeypatch.setattr("sys.argv", ["configure_labwc.py", str(config)])

    main()
    updated = config.read_text()
    assert 'key="A-F4"' in updated
    assert 'key="A-W-h"' in updated
    assert 'action name="HideCursor"' in updated

    main()
    assert config.read_text().count('key="A-W-h"') == 1
