@echo off
Script to update ccp from git
echo O update ira sobescrever qualquer modificacao feita aos arquivos na pasta.
set /p continuar="Deseja continuar? [y/n]"
if /i "%continuar%" neq "y" goto end
git init
git restore .
git remote add codigo https://codigo.petrobras.com.br/equipamentos-dinamicos/ccp.git
git pull codigo master
pause
:end
