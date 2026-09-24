' Axion Local baslatici: siyah pencere olmadan calisir.
' Axion zaten calisiyorsa sadece tarayiciyi acar; calismiyorsa baslatir ve hazir olunca acar.
Option Explicit

Dim sh, fso, root, python, url, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
python = root & "\.venv\Scripts\python.exe"
url = "http://localhost:8501"

If Not fso.FileExists(python) Then
  MsgBox "Axion kurulu degil. Once windows\kurulum.bat dosyasini calistir.", vbExclamation, "Axion Local"
  WScript.Quit 1
End If

If Not IsRunning() Then
  If Not fso.FolderExists(root & "\data") Then fso.CreateFolder root & "\data"
  sh.CurrentDirectory = root
  sh.Run "cmd /c """"" & python & """ -m streamlit run axion_local.py > ""data\axion.log"" 2>&1""", 0, False
  For i = 1 To 60
    WScript.Sleep 1000
    If IsRunning() Then Exit For
  Next
  If Not IsRunning() Then
    MsgBox "Axion baslatilamadi. Hata kaydi aciliyor; icerigini Claude'a veya GPT'ye gonder.", vbCritical, "Axion Local"
    sh.Run "notepad """ & root & "\data\axion.log""", 1, False
    WScript.Quit 1
  End If
End If

sh.Run url, 1, False

Function IsRunning()
  Dim http
  IsRunning = False
  On Error Resume Next
  Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
  http.setTimeouts 1000, 1000, 1000, 1000
  http.Open "GET", url & "/_stcore/health", False
  http.Send
  If Err.Number = 0 Then
    If http.Status = 200 Then IsRunning = True
  End If
  Err.Clear
  On Error GoTo 0
End Function
