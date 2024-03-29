<!-- : Begin batch script
@echo off
REM PUSHD "%~dp0"


REM author: Badr Elmers 2021-2023
REM description: refrenv = refresh environment. this is a better alternative to the chocolatey refreshenv for cmd
REM version: 1.0
REM https://github.com/badrelmers/RefrEnv
REM https://stackoverflow.com/questions/171588/is-there-a-command-to-refresh-environment-variables-from-the-command-prompt-in-w

REM ___USAGE_____________________________________________________________
REM usage: 
REM        call refrenv.bat        full refresh. refresh all non critical variables*, and refresh the PATH

REM debug:
REM        to debug what this script do create this variable in your parent script like that
REM        set debugme=yes
REM        then the folder containing the files used to set the variables will be open. Then see
REM        _NewEnv.cmd this is the file which run inside your script to setup the new variables, you
REM        can also revise the intermediate files _NewEnv.cmd_temp_.cmd and _NewEnv.cmd_temp2_.cmd 
REM        (those two contains all the variables before removing the duplicates and the unwanted variables)


REM you can also put this script in windows\systems32 or another place in your %PATH% then call it from an interactive console by writing refrenv

REM *critical variables: are variables which belong to cmd/windows and should not be refreshed normally like:
REM - windows vars:
REM ALLUSERSPROFILE APPDATA CommonProgramFiles CommonProgramFiles(x86) CommonProgramW6432 COMPUTERNAME ComSpec HOMEDRIVE HOMEPATH LOCALAPPDATA LOGONSERVER NUMBER_OF_PROCESSORS OS PATHEXT PROCESSOR_ARCHITECTURE PROCESSOR_ARCHITEW6432 PROCESSOR_IDENTIFIER PROCESSOR_LEVEL PROCESSOR_REVISION ProgramData ProgramFiles ProgramFiles(x86) ProgramW6432 PUBLIC SystemDrive SystemRoot TEMP TMP USERDOMAIN USERDOMAIN_ROAMINGPROFILE USERNAME USERPROFILE windir SESSIONNAME


REM ___INFO_____________________________________________________________
REM :: this script reload environment variables inside cmd every time you want environment changes to propagate, so you do not need to restart cmd after setting a new variable with setx or when installing new apps which add new variables ...etc


REM This is a better alternative to the chocolatey refreshenv for cmd, which solves a lot of problems like:

REM The Chocolatey refreshenv is so bad if the variable have some cmd meta-characters, see this test:
    REM add this to the path in HKCU\Environment: test & echo baaaaaaaaaad, and run the chocolatey refreshenv you will see that it prints baaaaaaaaaad which is very bad, and the new path is not added to your path variable.
    REM This script solve this and you can test it with any meta-character, even something so bad like:
    REM ; & % ' ( ) ~ + @ # $ { } [ ] , ` ! ^ | > < \ / " : ? * = . - _ & echo baaaad
    
REM refreshenv adds only system and user environment variables, but CMD adds volatile variables too (HKCU\Volatile Environment). This script will merge all the three and remove any duplicates.

REM refreshenv reset your PATH. This script append the new path to the old path of the parent script which called this script. It is better than overwriting the old path, otherwise it will delete any newly added path by the parent script.

REM This script solve this problem described in a comment by @Gene Mayevsky: refreshenv modifies env variables TEMP and TMP replacing them with values stored in HKCU\Environment. In my case I run the script to update env variables modified by Jenkins job on a slave that's running under SYSTEM account, so TEMP and TMP get substituted by %USERPROFILE%\AppData\Local\Temp instead of C:\Windows\Temp. This breaks build because linker cannot open system profile's Temp folder.

REM ________
REM this script solve things like that too:
REM The confusing thing might be that there are a few places to start the cmd from. In my case I run cmd from windows explorer and the environment variables did not change while when starting cmd from the "run" (windows key + r) the environment variables were changed.

REM In my case I just had to kill the windows explorer process from the task manager and then restart it again from the task manager.
REM Once I did this I had access to the new environment variable from a cmd that was spawned from windows explorer.

REM my conclusion:
REM if I add a new variable with setx, i can access it in cmd only if i run cmd as admin, without admin right i have to restart explorer to see that new variable. but running this script inside my script (who sets the variable with setx) solve this problem and i do not have to restart explorer


REM ________
REM windows recreate the path using three places at less:
REM the User namespace:    HKCU\Environment
REM the System namespace:  HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment
REM the Session namespace: HKCU\Volatile Environment
REM but the original chocolatey script did not add the volatile path. This script will merge all the three and remove any duplicates. this is what windows do by default too

REM there is this too which cmd seems to read when first running, but it contains only TEMP and TMP,so i will not use it
REM HKEY_USERS\.DEFAULT\Environment


REM ___TESTING_____________________________________________________________
REM to test this script with extreme cases do
    REM :: Set a bad variable
    REM add a var in reg HKCU\Environment as the following, and see that echo is not executed.  if you use refreshenv of chocolatey you will see that echo is executed which is so bad!
    REM so save this in reg:
    REM all 32 characters: & % ' ( ) ~ + @ # $ { } [ ] ; , ` ! ^ | > < \ / " : ? * = . - _ & echo baaaad
    REM and this:
    REM (^.*)(Form Product=")([^"]*") FormType="[^"]*" FormID="([0-9][0-9]*)".*$
    REM and use set to print those variables and see if they are saved without change ; refreshenv fail dramatically with those variables
    
    
REM invalid characters (illegal characters in file names) in Windows using NTFS
REM \ / : * ? "  < > |  and ^ in FAT 



REM __________________________________________________________________________________________
REM __________________________________________________________________________________________
REM __________________________________________________________________________________________
REM this is a hybrid script which call vbs from cmd directly
REM :: The only restriction is the batch code cannot contain - - > (without space between - - > of course)
REM :: The only restriction is the VBS code cannot contain </script>.
REM :: The only risk is the undocumented use of "%~f0?.wsf" as the script to load. Somehow the parser properly finds and loads the running .BAT script "%~f0", and the ?.wsf suffix mysteriously instructs CSCRIPT to interpret the script as WSF. Hopefully MicroSoft will never disable that "feature".
REM :: https://stackoverflow.com/questions/9074476/is-it-possible-to-embed-and-execute-vbscript-within-a-batch-file-without-using-a

if "%debugme%"=="yes" (
    echo RefrEnv - Refresh the Environment for CMD - ^(Debug enabled^)
) else (
    echo RefrEnv - Refresh the Environment for CMD
)

set "TEMPDir=%TEMP%\refrenv"
IF NOT EXIST "%TEMPDir%" mkdir "%TEMPDir%"
set "outputfile=%TEMPDir%\_NewEnv.cmd"


REM detect if DelayedExpansion is enabled
REM It relies on the fact, that the last caret will be removed only in delayed mode.
REM https://www.dostips.com/forum/viewtopic.php?t=6496
set "DelayedExpansionState=IsDisabled"
IF "^!" == "^!^" (
    REM echo DelayedExpansion is enabled
    set "DelayedExpansionState=IsEnabled"
)


REM :: generate %outputfile% which contain all the new variables
REM cscript //nologo "%~f0?.wsf" %1
cscript //nologo "%~f0?.wsf" "%outputfile%" %DelayedExpansionState%


REM ::set the new variables generated with vbscript script above
REM for this to work always it is necessary to use DisableDelayedExpansion or escape ! and ^ when using EnableDelayedExpansion, but this script already solve this, so no worry about that now, thanks to God
REM test it with some bad var like:
REM all 32 characters: ; & % ' ( ) ~ + @ # $ { } [ ] , ` ! ^ | > < \ / " : ? * = . - _ & echo baaaad
REM For /f delims^=^ eol^= %%a in (%outputfile%) do %%a
REM for /f "delims== tokens=1,2" %%G in (%outputfile%) do set "%%G=%%H"
For /f delims^=^ eol^= %%a in (%outputfile%) do set %%a


REM for safely print a variable with bad charachters do:
REM SETLOCAL EnableDelayedExpansion
REM echo "!z9!"
REM or
REM set z9
REM but generally paths and environment variables should not have bad metacharacters, but it is not a rule!


if "%debugme%"=="yes" (
    explorer "%TEMPDir%"
) else (
    rmdir /Q /S "%TEMPDir%"
)

REM cleanup
set "TEMPDir="
set "outputfile="
set "DelayedExpansionState="
set "debugme="


REM pause
exit /b



REM #############################################################################
REM :: to run jscript you have to put <script language="JScript"> directly after ----- Begin wsf script --->
----- Begin wsf script --->
<job><script language="VBScript">
REM #############################################################################
REM ### put you code here #######################################################
REM #############################################################################

REM based on itsadok script from here
REM https://stackoverflow.com/questions/171588/is-there-a-command-to-refresh-environment-variables-from-the-command-prompt-in-w

REM and it is faster as stated by this comment
REM While I prefer the Chocolatey code-wise for being pure batch code, overall I decided to use this one, since it's faster. (~0.3 seconds instead of ~1 second -- which is nice, since I use it frequently in my Explorer "start cmd here" entry) – 

REM and it is safer based on my tests, the Chocolatey refreshenv is so bad if the variable have some cmd metacharacters


Const ForReading = 1 
Const ForWriting = 2
Const ForAppending = 8 

Set WshShell = WScript.CreateObject("WScript.Shell")
filename=WScript.Arguments.Item(0)
DelayedExpansionState=WScript.Arguments.Item(1)

TMPfilename=filename & "_temp_.cmd"
Set fso = CreateObject("Scripting.fileSystemObject")
Set tmpF = fso.CreateTextFile(TMPfilename, TRUE)


set oEnvS=WshShell.Environment("System")
for each sitem in oEnvS
    tmpF.WriteLine(sitem)
next
SystemPath = oEnvS("PATH")

set oEnvU=WshShell.Environment("User")
for each sitem in oEnvU
    tmpF.WriteLine(sitem)
next
UserPath = oEnvU("PATH")

set oEnvV=WshShell.Environment("Volatile")
for each sitem in oEnvV
    tmpF.WriteLine(sitem)
next
VolatilePath = oEnvV("PATH")

set oEnvP=WshShell.Environment("Process")
REM i will not save the process env but only its path, because it have strange variables like  =::=::\ and  =F:=.... which seems to be added by vbscript
REM for each sitem in oEnvP
    REM tmpF.WriteLine(sitem)
REM next
REM here we add the actual session path, so we do not reset the original path, because maybe the parent script added some folders to the path, If we need to reset the path then comment the following line
ProcessPath = oEnvP("PATH")

REM merge System, User, Volatile, and process PATHs
NewPath = SystemPath & ";" & UserPath & ";" & VolatilePath & ";" & ProcessPath


REM ________________________________________________________________
REM :: remove duplicates from path
REM :: expand variables so they become like windows do when he read reg and create path, then Remove duplicates without sorting 
    REM why i will clean the path from duplicates? because:
    REM the maximum string length in cmd is 8191 characters. But string length doesnt mean that you can save 8191 characters in a variable because also the assignment belongs to the string. you can save 8189 characters because the remaining 2 characters are needed for "a="
   
    REM based on my tests: 
    REM when i open cmd as user , windows does not remove any duplicates from the path, and merge system+user+volatil path
    REM when i open cmd as admin, windows do: system+user path (here windows do not remove duplicates which is stupid!) , then it adds volatil path after removing from it any duplicates 

REM ' https://www.rosettacode.org/wiki/Remove_duplicate_elements#VBScript
Function remove_duplicates(list)
	arr = Split(list,";")
	Set dict = CreateObject("Scripting.Dictionary")
    REM ' force dictionary compare to be case-insensitive , uncomment to force case-sensitive
    dict.CompareMode = 1

	For i = 0 To UBound(arr)
		If dict.Exists(arr(i)) = False Then
			dict.Add arr(i),""
		End If
	Next
	For Each key In dict.Keys
		tmp = tmp & key & ";"
	Next
	remove_duplicates = Left(tmp,Len(tmp)-1)
End Function
 
REM expand variables
NewPath = WshShell.ExpandEnvironmentStrings(NewPath)
REM remove duplicates
NewPath=remove_duplicates(NewPath)

REM remove_duplicates() will add a ; to the end so lets remove it if the last letter is ;
If Right(NewPath, 1) = ";" Then 
    NewPath = Left(NewPath, Len(NewPath) - 1) 
End If
  
tmpF.WriteLine("PATH=" & NewPath)
tmpF.Close

REM ________________________________________________________________
REM :: exclude setting variables which may be dangerous to change

    REM when i run a script from task scheduler using SYSTEM user the following variables are the differences between the scheduler env and a normal cmd script, so i will not override those variables
    REM APPDATA=D:\Users\LLED2\AppData\Roaming
    REM APPDATA=D:\Windows\system32\config\systemprofile\AppData\Roaming

    REM LOCALAPPDATA=D:\Users\LLED2\AppData\Local
    REM LOCALAPPDATA=D:\Windows\system32\config\systemprofile\AppData\Local

    REM TEMP=D:\Users\LLED2\AppData\Local\Temp
    REM TEMP=D:\Windows\TEMP

    REM TMP=D:\Users\LLED2\AppData\Local\Temp
    REM TMP=D:\Windows\TEMP

    REM USERDOMAIN=LLED2-PC
    REM USERDOMAIN=WORKGROUP

    REM USERNAME=LLED2
    REM USERNAME=LLED2-PC$

    REM USERPROFILE=D:\Users\LLED2
    REM USERPROFILE=D:\Windows\system32\config\systemprofile

    REM i know this thanks to this comment
    REM The solution is good but it modifies env variables TEMP and TMP replacing them with values stored in HKCU\Environment. In my case I run the script to update env variables modified by Jenkins job on a slave that's running under SYSTEM account, so TEMP and TMP get substituted by %USERPROFILE%\AppData\Local\Temp instead of C:\Windows\Temp. This breaks build because linker cannot open system profile's Temp folder. – Gene Mayevsky Sep 26 '19 at 20:51


REM Delete Lines of a Text File Beginning with a Specified String
REM those are the variables which should not be changed by this script 
arrBlackList = Array("ALLUSERSPROFILE=", "APPDATA=", "CommonProgramFiles=", "CommonProgramFiles(x86)=", "CommonProgramW6432=", "COMPUTERNAME=", "ComSpec=", "HOMEDRIVE=", "HOMEPATH=", "LOCALAPPDATA=", "LOGONSERVER=", "NUMBER_OF_PROCESSORS=", "OS=", "PATHEXT=", "PROCESSOR_ARCHITECTURE=", "PROCESSOR_ARCHITEW6432=", "PROCESSOR_IDENTIFIER=", "PROCESSOR_LEVEL=", "PROCESSOR_REVISION=", "ProgramData=", "ProgramFiles=", "ProgramFiles(x86)=", "ProgramW6432=", "PUBLIC=", "SystemDrive=", "SystemRoot=", "TEMP=", "TMP=", "USERDOMAIN=", "USERDOMAIN_ROAMINGPROFILE=", "USERNAME=", "USERPROFILE=", "windir=", "SESSIONNAME=")

Set objFS = CreateObject("Scripting.FileSystemObject")
Set objTS = objFS.OpenTextFile(TMPfilename, ForReading)
strContents = objTS.ReadAll
objTS.Close

TMPfilename2= filename & "_temp2_.cmd"
arrLines = Split(strContents, vbNewLine)
Set objTS = objFS.OpenTextFile(TMPfilename2, ForWriting, True)

REM this is the equivalent of findstr /V /I /L  or  grep -i -v  , i don t know a better way to do it, but it works fine
For Each strLine In arrLines
    bypassThisLine=False
    For Each BlackWord In arrBlackList
        If Left(UCase(LTrim(strLine)),Len(BlackWord)) = UCase(BlackWord) Then
            bypassThisLine=True
        End If
    Next
    If bypassThisLine=False Then
        objTS.WriteLine strLine
    End If
Next

REM ____________________________________________________________
REM :: expand variables because registry save some variables as unexpanded %....%
REM :: and escape ! and ^ for cmd EnableDelayedExpansion mode

set f=fso.OpenTextFile(TMPfilename2,ForReading)
REM Write file:  ForAppending = 8 ForReading = 1 ForWriting = 2 , True=create file if not exist
set fW=fso.OpenTextFile(filename,ForWriting,True)
Do Until f.AtEndOfStream
    LineContent = f.ReadLine
    REM expand variables
    LineContent = WshShell.ExpandEnvironmentStrings(LineContent)
    
    REM _____this part is so important_____
    REM if cmd delayedexpansion is enabled in the parent script which calls this script then bad thing happen to variables saved in the registry if they contain ! . if var have ! then ! and ^ are removed; if var do not have ! then ^ is not removed . to understand what happens read this :
    REM how cmd delayed expansion parse things
    REM https://stackoverflow.com/questions/4094699/how-does-the-windows-command-interpreter-cmd-exe-parse-scripts/7970912#7970912
    REM For each parsed token, first check if it contains any !. If not, then the token is not parsed - important for ^ characters. If the token does contain !, then scan each character from left to right:
    REM     - If it is a caret (^) the next character has no special meaning, the caret itself is removed
    REM     - If it is an exclamation mark, search for the next exclamation mark (carets are not observed anymore), expand to the value of the variable.
    REM         - Consecutive opening ! are collapsed into a single !
    REM         - Any remaining unpaired ! is removed
    REM ...
    REM Look at next string of characters, breaking before !, :, or <LF>, and call them VAR

    REM conclusion:
    REM when delayedexpansion is enabled and var have ! then i have to escape ^ and ! ,BUT IF VAR DO NOT HAVE ! THEN DO NOT ESCAPE ^  .this made me crazy to discover
    REM when delayedexpansion is disabled then i do not have to escape anything
    
    If DelayedExpansionState="IsEnabled" Then
        If InStr(LineContent, "!") > 0 Then
            LineContent=Replace(LineContent,"^","^^")
            LineContent=Replace(LineContent,"!","^!")
        End If
    End If
    REM __________
    
    fW.WriteLine(LineContent)
Loop

f.Close
fW.Close

REM #############################################################################
REM ### end of vbscript code ####################################################
REM #############################################################################
REM this must be at the end for the hybrid trick, do not remove it
</script></job>
