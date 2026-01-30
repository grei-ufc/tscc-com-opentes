# Makefile para projeto COSIMA OMNeT++
# Baseado nos 5 arquivos .cc existentes

# Nome do executável
TARGET = cosima_omnetpp_project

# Arquivos fonte (os 5 arquivos .cc que temos)
SRCS = \
    AgentAppTcp.cc \
    AgentAppUdp.cc \
    CosimaScenarioManager.cc \
    CosimaScheduler.cc \
    CosimaSchedulerModule.cc

# Arquivos objeto (.o)
OBJS = $(SRCS:.cc=.o)

# Compilador
CXX = clang++

# Flags do compilador
CXXFLAGS = -std=c++14 -O2 -fPIC -g

# Diretórios de include (serão sobrescritos pelo Docker)
# Diretórios de include
INCLUDES = -I. \
           -I./cosima_core/messages \
           -I$(OMNETPP_ROOT)/include \
           -I$(INET_PATH)/src \
           -I$(INET_PATH)/src/inet

# Flags do linker
LDFLAGS = -L$(OMNETPP_ROOT)/lib \
          -L$(INET_PATH)/src

# Bibliotecas
LIBS = -loppenvir \
       -loppsim \
       -lnedxml \
       -lnedl \
       -lINET

# Regra principal - compilar tudo
all: $(TARGET)

# Linkar os objetos para criar o executável
$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $^ $(LIBS)

# Compilar cada arquivo .cc para .o
%.o: %.cc
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Limpar arquivos gerados
clean:
	rm -f $(OBJS) $(TARGET)
	rm -f *.o *.so *.a

# Limpeza profunda
distclean: clean
	rm -f *~

# Ajuda
help:
	@echo "Makefile para projeto COSIMA OMNeT++"
	@echo ""
	@echo "Uso:"
	@echo "  make              - Compilar projeto"
	@echo "  make clean        - Remover arquivos gerados"
	@echo "  make distclean    - Limpeza completa"
	@echo "  make help         - Mostrar esta ajuda"
	@echo ""
	@echo "Variáveis de ambiente necessárias:"
	@echo "  OMNETPP_ROOT      - Caminho para OMNeT++"
	@echo "  INET_PATH         - Caminho para INET framework"
	@echo ""
	@echo "Arquivos fonte:"
	@echo "  $(SRCS)"

.PHONY: all clean distclean help
