#!/bin/bash 

cd /home/pirate/badges_UCN/badges_UCN

numero=TRUE

while [ $numero ]
do
    #Validar si se inserto un numero o no
	
	echo "Escribe la fecha de la actividad: yyyy-mm-dd";
	read number
	
	#Probar si existe la actividad
	foo="actividad_"
	foo+=$number

	if [ -d /$foo/ ];
	then
		echo "La actividad ya existe, por favor escribe una nueva fecha."
	else
		numero=FALSE
	fi		
		
     #echo -e "Acción $i ejecutada.\n"
     #let i=$i+1
done
#Crear Carpeta de Actividad
mkdir $foo
echo "Actividad nueva creada."

#Copiar data a la carpeta creada
cp /home/pirate/badges_UCN/openbadge-hub-py/data/proximity_data.txt proximity_data.txt
cp /home/pirate/badges_UCN/openbadge-hub-py/data/audio_data.txt audio_data.txt


# UpToGit 0.1
# Actualiza facilmente tu repositorio Git
# (CC) 2011 Alfonso Saavedra "Son Link"
# http://sonlinkblog.blogspot.com
# Bajo licencia GNU/GPL

# Modo de uso: copia o mueve este script a /usr/bin o /usr/local/bin y desde el directorio donde se encuentre la copia de un repo git, ejecútalo de esta manera:
# uptogit <ficheros>

# Comprobamos si el directorio en el que estamos es de un repositorio git
if [ ! -d '.git' ]; then
	echo 'Esta carpeta no contiene un repositorio Git'
	exit -1
fi

# Ahora comprobamos si se le paso algun parametro
if [ $# == 0 ]; then
	echo "UpToGit: ¡Error! No se le a pasado ningún parámetro"
	echo "uptogit fichero1 fichero2 ... ficheroN"
	exit -1
else
	# Recorremos los parametros para comprobar si son ficheros o directorios
	for file in $*; do
		if [ ! -e $file ]; then
			echo "UpToGit: El archivo o directorio $file no existe"
			exit -1
		fi
	done
	
	# Si llegamos hasta aquí, indicamos a Git los archivos a subir
	git add $*
	
	# Esto nos pedira el mensaje del commit
	echo "Introduce un mensaje de comentario:"
	read TXT
	git commit -m "$TXT"

	# Y terminamos subiendo los archivos
	#git push https://badges-UCN:socialucn1@badges_UCN.git

	#git push https://badges:socialucn1@badges_UCN.git --all 
	
	echo "Usuario: badges-UCN"
	echo "Password: socialucn1"
	git push origin master -f

fi