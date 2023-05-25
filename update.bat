@echo off
Script to update ccp from git
echo O update ira sobescrever qualquer modificacao feita aos arquivos na pasta.
set /p continuar="Deseja continuar? [y/n]"
if /i "%continuar%" neq "y" goto end
git init
git restore .
git remote add upstream https://github.com/petrobras/ccp.git
git pull upstream main
pause
:end
