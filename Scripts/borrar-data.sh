echo "La data medida sera eliminada del directorio de medicion"
echo "ESTO NO TIENE VUELTA ATRAS"
echo "Asegurate que la data se encuentre en el repositorio en la nube (https://github.com/crcandia/badges_UCN)"
echo "deseas continuar? si/no"
read txt

if [ "$txt" = "si" ];
then
	rm /home/pirate/badges_UCN/openbadge-hub-py/data/proximity_data.txt
	rm /home/pirate/badges_UCN/openbadge/hub/py/data/proximity_data.txt
else
	echo "Revisa la pagina de github > https://github.com/crcandia/badges_UCN"
fi
