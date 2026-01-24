#!/bin/bash

echo "========================================="
echo "VERIFICAÇÃO COSIMA - Laiza"
echo "========================================="
echo ""

# Status dos containers
echo "1. STATUS DOS CONTAINERS:"
docker-compose ps 2>/dev/null || echo "docker-compose não disponível"

echo ""
echo "2. CONTAINERS EM EXECUÇÃO:"
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"

echo ""
echo "3. INFORMAÇÕES DE SEPARAÇÃO:"
mosaik_id=$(docker inspect -f '{{.Id}}' cosima-mosaik 2>/dev/null | cut -c1-12)
omnet_id=$(docker inspect -f '{{.Id}}' cosima-omnet 2>/dev/null | cut -c1-12)

if [ -z "$mosaik_id" ]; then
    echo " Mosaik: NÃO ENCONTRADO"
else
    echo "OK Mosaik: $mosaik_id"
fi

if [ -z "$omnet_id" ]; then
    echo " OMNeT++: NÃO ENCONTRADO"
else
    echo "OK  OMNeT++: $omnet_id"
fi

echo ""
echo "4. VERIFICAÇÃO DE SEPARAÇÃO:"
if [ -n "$mosaik_id" ] && [ -n "$omnet_id" ]; then
    if [ "$mosaik_id" != "$omnet_id" ]; then
        echo "  MOSAIK e OMNET++ estão em CONTAINERS DIFERENTES!"
    else
        echo " ERROR: MOSAIK e OMNET++ estão no MESMO container!"
    fi
else
    echo " ATENCÃO! ALGUM CONTAINER NÃO ESTÁ RODANDO"
fi

echo ""
echo "5. IPS DOS CONTAINERS:"
echo "Mosaik IP:  $(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' cosima-mosaik 2>/dev/null || echo 'N/A')"
echo "OMNeT++ IP: $(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' cosima-omnet 2>/dev/null || echo 'N/A')"

echo ""
echo "6. TESTE DE CONEXÃO:"
if docker exec cosima-mosaik ping -c 1 cosima-omnet > /dev/null 2>&1; then
    echo " Mosaik consegue acessar OMNeT++"
else
    echo " Mosaik NÃO consegue acessar OMNeT++"
fi
