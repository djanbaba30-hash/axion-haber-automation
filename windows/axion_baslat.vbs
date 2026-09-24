' Axion Local baslatici: siyah pencere olmadan calisir.
' Sunucu zaten calisiyorsa sadece tarayiciyi acar; calismiyorsa arka planda baslatir.
' /arkaplan parametresi: tarayici acilmaz (Windows acilisinda kullanilir).
Option Explicit

Dim sh, fso, root, python, url, background, i, started
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
python = root & "\.venv\Scripts\python.exe"
url = "http://localhost:8501"
background = False
If WScript.Arguments.Count > 0 Then background = (LCase(WScript.Arguments(0)) = "/arkaplan")

If Not fso.FileExists(python) Then
  MsgBox "Axion kurulu degil. Once windows\kurulum.bat dosyasini calistir.", vbExclamation, "Axion Local"
  WScript.Quit 1
End If

If Not IsRunning() Then
  If Not fso.FolderExists(root & "\data") Then fso.CreateFolder root & "\data"
  sh.CurrentDirectory = root
  sh.Environment("Process")("AXION_LOCAL") = "1"
  sh.Run "cmd /c """"" & python & """ -m streamlit run axion_local.py --server.port 8501 --server.headless true --server.maxUploadSize 4096 --browser.gatherUsageStats false --client.toolbarMode minimal > ""data\axion.log"" 2>&1""", 0, False
  started = False
  For i = 1 To 60
    WScript.Sleep 1000
    If IsRunning() Then
      started = True
      Exit For
    End If
  Next
  If Not started Then
    MsgBox "Axion baslatilamadi. Hata kaydi aciliyor; icerigini Claude'a gonder.", vbCritical, "Axion Local"
    sh.Run "notepad """ & root & "\data\axion.log""", 1, False
    WScript.Quit 1
  End If
End If

If Not background Then sh.Run url, 1, False

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
