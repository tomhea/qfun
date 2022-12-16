import os

import easyibmq
from qiskit.circuit.random import random_circuit


def create_circuit__h_cx() -> easyibmq.QuantumCircuit:
    qc = easyibmq.QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure((0, 1), (0, 1))

    return qc


def create_circuit__x_cx() -> easyibmq.QuantumCircuit:
    qc = easyibmq.QuantumCircuit(2, 2)
    qc.x(0)
    qc.cx(0, 1)
    qc.measure((0, 1), (0, 1))

    return qc


def main():
    circuits = [create_circuit__h_cx(), create_circuit__x_cx()] * 51
    circuits += [random_circuit(num_qubits=4, depth=3, measure=True) for _ in range(100)]

    hists = easyibmq.execute_jobs(circuits, shots=1000)

    os.makedirs('results', exist_ok=True)
    easyibmq.save_results('results', hists, circuits)


if __name__ == '__main__':
    main()
