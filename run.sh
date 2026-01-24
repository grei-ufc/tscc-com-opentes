#!/bin/bash

echo "======================================"
echo "  COSIMA Smart Grid Simulator"
echo "======================================"
echo ""
echo "Comandos disponíveis:"
echo "  1. ./run.sh build     - Construir imagem"
echo "  2. ./run.sh start     - Iniciar containers"
echo "  3. ./run.sh stop      - Parar containers"
echo "  4. ./run.sh shell     - Entrar no container"
echo "  5. ./run.sh logs      - Ver logs"
echo "  6. ./run.sh clean     - Limpar tudo"
echo "  7. ./run.sh test      - Testar ambiente"
echo ""

case "$1" in
    build)
        echo "Construindo imagem Docker..."
        docker-compose build
        ;;
    start)
        echo "Iniciando serviços..."
        docker-compose up -d
        echo "Acesse resultados em: http://localhost:8000"
        ;;
    stop)
        echo "Parando serviços..."
        docker-compose down
        ;;
    shell)
        echo "Abrindo terminal no container..."
        docker-compose exec cosima-simulator bash
        ;;
    logs)
        echo "Mostrando logs..."
        docker-compose logs -f
        ;;
    clean)
        echo "Removendo containers e volumes..."
        docker-compose down -v
        docker system prune -f
        ;;
    test)
        echo "Testando ambiente..."
        docker-compose run --rm cosima-simulator python --version
        ;;
    *)
        echo "Uso: ./run.sh {build|start|stop|shell|logs|clean|test}"
        ;;
esac

