#!/bin/bash

echo "========================================"
echo "  COSIMA Smart Grid Co-Simulation"
echo "========================================"

case "$1" in
    build-all)
        echo "🔨 Construindo TODOS os serviços..."
        docker-compose build
        ;;
    
    build-omnet)
        echo "🔨 Construindo apenas OMNeT++..."
        docker-compose build omnet
        ;;
    
    start)
        echo "🚀 Iniciando ambiente COSIMA..."
        docker-compose up -d
        echo ""
        echo "✅ Serviços iniciados:"
        echo "   OMNeT++:   docker exec -it cosima-omnet bash"
        echo "   MOSAIK:    http://localhost:5000"
        echo "   Web View:  http://localhost:8000"
        ;;
    
    stop)
        echo "🛑 Parando serviços..."
        docker-compose down
        ;;
    
    logs)
        echo "📋 Mostrando logs..."
        docker-compose logs -f
        ;;
    
    shell-omnet)
        echo "🐚 Entrando no container OMNeT++..."
        docker exec -it cosima-omnet bash
        ;;
    
    shell-mosaik)
        echo "🐚 Entrando no container MOSAIK..."
        docker exec -it cosima-mosaik bash
        ;;
    
    run-simulation)
        echo "⚡ Executando simulação..."
        docker-compose run --rm cosima-core
        ;;
    
    test)
        echo "🧪 Testando componentes..."
        echo ""
        echo "1. Testando OMNeT++..."
        docker-compose run --rm omnet python --version || echo "OMNeT++ não construído ainda"
        echo ""
        echo "2. Testando MOSAIK..."
        docker-compose run --rm mosaik python -c "import mosaik; print('MOSAIK OK')" 2>/dev/null || echo "MOSAIK não construído ainda"
        echo ""
        echo "3. Testando COSIMA Core..."
        docker-compose run --rm cosima-core python --version || echo "COSIMA Core não construído ainda"
        ;;
    
    clean)
        echo "🧹 Limpando..."
        docker-compose down -v
        docker system prune -f
        rm -rf mosaik_results/* omnet_results/* cosima_results/* 2>/dev/null
        echo "✅ Limpeza concluída!"
        ;;
    
    status)
        echo "📊 Status dos serviços:"
        docker-compose ps
        echo ""
        echo "📁 Resultados disponíveis:"
        ls -la mosaik_results/ omnet_results/ cosima_results/ 2>/dev/null || echo "Diretórios de resultados vazios ou não existem"
        ;;
    
    help|*)
        echo "Uso: ./run_cosima.sh {comando}"
        echo ""
        echo "Comandos disponíveis:"
        echo "  build-all        - Construir todos serviços"
        echo "  build-omnet      - Construir apenas OMNeT++ (RECOMENDADO primeiro)"
        echo "  start            - Iniciar serviços em background"
        echo "  stop             - Parar serviços"
        echo "  logs             - Ver logs"
        echo "  shell-omnet      - Terminal no OMNeT++"
        echo "  shell-mosaik     - Terminal no MOSAIK"
        echo "  run-simulation   - Executar simulação"
        echo "  test             - Testar componentes"
        echo "  status           - Ver status dos serviços"
        echo "  clean            - Limpar tudo (cuidado!)"
        echo "  help             - Mostrar esta ajuda"
        echo ""
        echo "🎯 Fluxo recomendado para iniciantes:"
        echo "  1. ./run_cosima.sh build-omnet    # Construir OMNeT (30-60 min)"
        echo "  2. ./run_cosima.sh test           # Testar construção"
        echo "  3. ./run_cosima.sh start          # Iniciar serviços"
        echo "  4. ./run_cosima.sh shell-omnet    # Entrar no OMNeT"
        echo "  5. ./run_cosima.sh status         # Verificar status"
        echo ""
        echo "🌐 URLs após iniciar:"
        echo "  - MOSAIK API:    http://localhost:5000"
        echo "  - Web Viewer:    http://localhost:8000"
        echo "  - COSIMA Core:   porta 8080"
        ;;
esac
