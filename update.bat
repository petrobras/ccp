@echo off
Script to update ccp from git
echo Updating ccp...
git init
git remote add codigo https://codigo.petrobras.com.br/equipamentos-dinamicos/ccp.git
git pull codigo master
pause
