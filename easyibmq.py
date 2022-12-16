import json
from time import time
from multiprocessing import Pool
from typing import Optional, Dict, Union, List

import easygui
from qiskit.providers.ibmq.managed import IBMQManagedResultDataNotAvailable
from tqdm import tqdm

import qiskit
from matplotlib import pyplot as plt

from qiskit import IBMQ, transpile
from qiskit.providers.ibmq import IBMQJobManager, IBMQAccountError
from qiskit.tools.monitor import job_monitor

from qiskit import QuantumCircuit
from qiskit.visualization import plot_histogram as plot


CIRCUIT_DRAWING_MAX_LINE = 1000


class PrintTimer:
    """
    prints the time a code segment took.
    usage:
    with PrintTimer('long_function time: '):
        long_function()
    """
    MIN_LENGTH = 22

    def __init__(self, init_message: str):
        self.init_message = init_message.ljust(PrintTimer.MIN_LENGTH, ' ')

    def __enter__(self) -> None:
        self.start_time = time()
        print(self.init_message, end='', flush=True)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        print(f'{time() - self.start_time:.3f}s')


def _get_backend_info(backend) -> str:
    pending_jobs = backend.status().pending_jobs

    try:
        qubit_count = len(backend.properties().qubits)
        gates = ' '.join(sorted(sorted(backend.configuration().basis_gates), key=lambda x:len(x)))
    except AttributeError:
        qubit_count = "simulated"
        gates = ''

    return f"{backend.name()}\n\n{pending_jobs} queued\n{qubit_count} qubits\n{gates}"


def query_backend_name(*, hide_simulated: bool = False) -> str:
    """
    query the user to choose a backend.

    @param hide_simulated: don't show the simulated backends

    @raises LookupError: if no name was chosen, or if no backend was found

    @returns: the chosen name
    """
    provider = IBMQ.get_provider("ibm-q")
    backends = provider.backends()

    with PrintTimer('loading backends...'), Pool() as p:
        choices = list(p.map(_get_backend_info, backends))

    if hide_simulated:
        choices = list(filter(lambda x: not x.endswith('\nsimulated qubits'), choices))

    if len(choices) == 0:
        raise LookupError("No active backend was found")

    choice = easygui.buttonbox("Please choose a backend:", "Backend", choices)
    if choice is None:
        raise LookupError("You must choose a backend")

    return choice.split('\n')[0]


def _get_backend_by_name(name: str):
    provider = IBMQ.get_provider("ibm-q")

    try:
        return provider.get_backend(name)
    except qiskit.exceptions.QiskitError:
        raise LookupError(f"No such backend name: {name}")


def execute_jobs(circuits: Union[List[qiskit.QuantumCircuit], qiskit.QuantumCircuit], shots: Optional[int] = None, *,
                 backend_name: Optional[str] = None, hide_simulated: bool = False,
                 monitor: bool = True, force_account_reload: bool = False):
    """
    runs the circuit on an ibm-q computer, and returns the histogram result.

    @param circuits: the quantum circuit(s) to execute.
    @param shots: times to repeat each circuit run (if unspecified, using the backend-default).
    @param backend_name: the ibm-q backend name; if unspecified, the user is queried with all possible options
    @param hide_simulated: if querying user for a backend name, don't show the simulated backends
    @param monitor: print an updating status (queue position) for the last job
    @param force_account_reload: force reloading the IBMQ-account

    @raises LookupError: if can't find backend
    @raises RuntimeError: if can't authenticate the IBMQ account

    @returns: an active job. you may call get_hist on it
    """
    if isinstance(circuits, qiskit.QuantumCircuit):
        circuits = [circuits]

    if force_account_reload or not IBMQ.active_account():
        with PrintTimer('loading account...'):
            try:
                IBMQ.load_account()
            except IBMQAccountError as e:
                raise RuntimeError(f'{str(e)}\n'
                                   f'Failed to authenticate IBMQ account. This might solve:\n'
                                   f'1. register in quantum-computing.ibm.com/\n'
                                   f'2. Execute once IBMQ.save_account("token") on your machine')

    if backend_name is None:
        backend_name = query_backend_name(hide_simulated=hide_simulated)
    backend = _get_backend_by_name(backend_name)

    with PrintTimer('transpile circuits...'):
        circuits = transpile(circuits, backend=backend)

    job_set = IBMQJobManager().run(circuits, backend=backend, shots=shots)

    num_of_jobs = len(job_set.jobs())
    if num_of_jobs >= 2:
        print(f"The execution is split into {num_of_jobs} jobs.")

    if monitor and num_of_jobs >= 1:
        job_monitor(job_set.jobs()[-1])

    results = job_set.results()
    hists = []
    for i in range(len(circuits)):
        try:
            hists.append(dict(results.get_counts(i)))
        except IBMQManagedResultDataNotAvailable:
            hists.append(None)
            print(f'\rResult data not found in experiment {i}         ')
    return hists


def save_results(results_dir_path: str, hists: List[Dict[str, int]], circuits: Optional[List[QuantumCircuit]] = None) -> None:
    """
    save the results to a json file (results.txt), and to many graph-pictures (circuit_i.png).

    @param results_dir_path: the directory to save to
    @param hists: the results' histograms, as given by execute_jobs
    @param circuits: optional, if specified then the circuits' drawing and names will appear on the graph-pictures
    """
    with open(f'{results_dir_path}/results.txt', 'w') as json_result:
        json.dump(hists, json_result)

    for i, hist in tqdm(list(enumerate(hists)), desc="saving graphs"):
        plot(hist if hist else {'Failed': 1})
        if circuits:
            circuit = circuits[i]
            plt.title(f'{circuit.draw(fold=CIRCUIT_DRAWING_MAX_LINE, vertical_compression="high", cregbundle=True)}'
                      f'\n\n{circuit.name}\n', family='monospace')
        plt.savefig(f'{results_dir_path}/circuit_{i}.png', bbox_inches='tight')

