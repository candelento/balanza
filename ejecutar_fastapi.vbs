Set WshShell = CreateObject("WScript.Shell")

' Obtener la ruta del directorio donde está el script
ScriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Cambiar al directorio de la aplicación
WshShell.CurrentDirectory = ScriptDir

' Ejecutar la aplicación FastAPI
' Usar cmd /k para mantener la ventana abierta después de la ejecución
WshShell.Run "cmd /k python main.py", 1, False

' Mensaje opcional para confirmar que se inició
WScript.Echo "FastAPI iniciado en http://localhost:8001"