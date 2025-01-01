' correct way to hide console and run non 'windows' subsystem program
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "uv run python -m duckdns", 0, True
Set WshShell = Nothing
