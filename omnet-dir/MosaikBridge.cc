/**
 * @file MosaikBridge.cc
 * @brief Ponte de comunicação entre OMNeT++ e Mosaik via ZeroMQ.
 */

#include <omnetpp.h>
#include <zmq.hpp>
#include <nlohmann/json.hpp>
#include <string>

using namespace omnetpp;
using json = nlohmann::json;

class MosaikBridge : public cSimpleModule {
  private:
    zmq::context_t context{1};
    zmq::socket_t socket{context, zmq::socket_type::rep};
    cMessage *stepMsg = nullptr;

    void applyInputs(json j);

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
};

Define_Module(MosaikBridge);

void MosaikBridge::applyInputs(json j) {
    if (j.contains("inputs") && !j["inputs"].is_null()) {
        json inputs = j["inputs"];
        for (auto& [nodeName, nodeAttributes] : inputs.items()) {
            cModule *targetNode = getParentModule()->getSubmodule(nodeName.c_str());
            if (targetNode != nullptr) {
                for (auto& [attrName, sources] : nodeAttributes.items()) {
                    if (targetNode->hasPar(attrName.c_str())) {
                        if (sources.begin().value().is_number()) {
                            double totalValue = 0.0;
                            for (auto& [sourceEntity, value] : sources.items()) {
                                totalValue += value.get<double>();
                            }
                            targetNode->par(attrName.c_str()).setDoubleValue(totalValue);
                        } 
                        else if (sources.begin().value().is_string()) {
                            std::string combinedStr = "";
                            for (auto& [sourceEntity, value] : sources.items()) {
                                std::string valStr = value.get<std::string>();
                                if (!valStr.empty()) {
                                    combinedStr = valStr;
                                }
                            }
                            // Só injeta no OMNeT++ se a mensagem não for vazia
                            if (!combinedStr.empty()) {
                                targetNode->par(attrName.c_str()).setStringValue(combinedStr.c_str());
                            }
                        }
                    }
                }
            }
        }
    }
}

void MosaikBridge::initialize() {
    socket.bind("tcp://*:5555");
    bool scenario_ready = false;
    
    while (!scenario_ready) {
        zmq::message_t request;
        socket.recv(request, zmq::recv_flags::none);
        
        std::string msg_str(static_cast<char*>(request.data()), request.size());
        json j = json::parse(msg_str);

        if (j["action"] == "create") {
            std::string modelName = j["params"]["node_type"];
            std::string entityId = j["eid"];

            cModuleType *moduleType = cModuleType::find(modelName.c_str());
            json response;

            if (moduleType) {
                cModule *newModule = moduleType->create(entityId.c_str(), getParentModule());
                newModule->finalizeParameters();
                newModule->buildInside();
                newModule->scheduleStart(simTime());
                response = {{"status", "ok"}};
            } else {
                response = {{"status", "error", "reason", "Modulo nao encontrado"}};
            }
            socket.send(zmq::buffer(response.dump()), zmq::send_flags::none);
        } 
        else if (j["action"] == "connect") {
            socket.send(zmq::buffer(json({{"status", "ok"}}).dump()), zmq::send_flags::none);
        }
        else if (j["action"] == "step") {
            applyInputs(j);
            
            scenario_ready = true;
            stepMsg = new cMessage("next_step");
            scheduleAt(simTime() + 1.0, stepMsg);
        }
    }
}

void MosaikBridge::handleMessage(cMessage *msg) {
    if (msg == stepMsg) {
        json data_json = json::object();

        for (cModule::SubmoduleIterator it(getParentModule()); !it.end(); ++it) {
            cModule *submod = *it;
            if (submod == this) continue; 

            std::string nodeName = submod->getName();
            json node_data = json::object();

            node_data["status"] = submod->hasPar("status") ? submod->par("status").stdstringValue() : "unknown";
            node_data["data_out"] = submod->hasPar("data_out") ? submod->par("data_out").doubleValue() : 0.0;

            if (submod->hasPar("val_out")) {
                node_data["val_out"] = submod->par("val_out").stdstringValue();
                submod->par("val_out").setStringValue("");
            }

            if (submod->hasPar("packets_sent")) node_data["packets_sent"] = submod->par("packets_sent").doubleValue();
            if (submod->hasPar("packets_received")) node_data["packets_received"] = submod->par("packets_received").doubleValue();
            if (submod->hasPar("last_latency")) node_data["last_latency"] = submod->par("last_latency").doubleValue();
            if (submod->hasPar("last_packet_size")) node_data["last_packet_size"] = submod->par("last_packet_size").doubleValue();
            if (submod->hasPar("packets_dropped")) node_data["packets_dropped"] = submod->par("packets_dropped").doubleValue();
            if (submod->hasPar("current_jitter")) node_data["current_jitter"] = submod->par("current_jitter").doubleValue();

            data_json[nodeName] = node_data;
        }

        json response = {
            {"status", "ok"},
            {"data", data_json}
        };
        
        socket.send(zmq::buffer(response.dump()), zmq::send_flags::none);

        zmq::message_t next_request;
        socket.recv(next_request, zmq::recv_flags::none);
        
        std::string msg_str(static_cast<char*>(next_request.data()), next_request.size());
        json j = json::parse(msg_str);

        if (j["action"] == "step") {
            applyInputs(j); // Reaproveita a função para ler os passos t=1, t=2...
            scheduleAt(simTime() + 1.0, stepMsg);
        } else if (j["action"] == "stop") {
            endSimulation();
        }
    } else {
        delete msg; 
    }
}

void MosaikBridge::finish() {
    if (stepMsg) cancelAndDelete(stepMsg);
    socket.close();
}