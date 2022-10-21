from typing import Dict

import json
import matplotlib.pyplot as plt

import easyibmq


def show_result(job) -> None:
    hist = easyibmq.get_hist(job)

    with open('result.txt', 'w') as json_result:
        json.dump(hist, json_result)

    easyibmq.plot(hist, filename='result.png')
    plt.show()


def save_circuit(circuit: easyibmq.QuantumCircuit):
    with open('circuit.txt', 'wb') as f:
        f.write(str(circuit).encode('utf-8'))

    circuit.draw(output='mpl', filename='circuit.png')


def create_circuit__h_cx() -> easyibmq.QuantumCircuit:
    circuit = easyibmq.QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure((0, 1), (0, 1))

    return circuit


def create_circuit__x_cx() -> easyibmq.QuantumCircuit:
    circuit = easyibmq.QuantumCircuit(2, 2)
    circuit.x(0)
    circuit.cx(0, 1)
    circuit.measure((0, 1), (0, 1))

    return circuit


def main():
    # if first time, register in https://quantum-computing.ibm.com/
    # Then execute once:
    # IBMQ.save_account(open("token.txt", "r").read())

    circuit1 = create_circuit__h_cx()
    circuit2 = create_circuit__x_cx()

    backend_name = easyibmq.query_backend_name()    # = 'ibmq_belem'
    job1 = easyibmq.execute_job(circuit1, 1000, backend_name=backend_name)
    job2 = easyibmq.execute_job(circuit2, 1000, backend_name=backend_name)

    show_result(job1)
    show_result(job2)


if __name__ == '__main__':
    main()
