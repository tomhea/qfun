from time import time
from typing import Optional, Dict

import easygui
from multiprocessing import Pool

import qiskit
from qiskit import IBMQ
from qiskit.tools.monitor import job_monitor


from qiskit import QuantumCircuit
from qiskit.visualization import plot_histogram as plot


class PrintTimer:
    """
    prints the time a code segment took.
    usage:
    with PrintTimer('long_function time: '):
        long_function()
    """
    def __init__(self, init_message: str):
        self.init_message = init_message

    def __enter__(self) -> None:
        self.start_time = time()
        print(self.init_message, end='', flush=True)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        print(f'{time() - self.start_time:.3f}s')


def _get_backend_info(backend) -> str:
    pending_jobs = backend.status().pending_jobs

    try:
        qubit_count = len(backend.properties().qubits)
    except AttributeError:
        qubit_count = "simulated"

    return f"{backend.name()}\n\n{pending_jobs} queued\n{qubit_count} qubits"


def query_backend_name(*, skip_simulated: bool = True) -> str:
    """
    ask the user to choose a backend.

    @param skip_simulated: hide the simulated backends

    @raises LookupError: if no name was chosen, or if no backend was found

    @returns: the chosen name
    """
    backends = IBMQ.get_provider("ibm-q").backends()

    title = "Backend"
    body = "Please choose a backend:"

    with PrintTimer('loading backends... '), Pool() as p:
        choices = list(p.map(_get_backend_info, backends))

    if skip_simulated:
        choices = list(filter(lambda x: not x.endswith('\nsimulated qubits'), choices))

    if len(choices) == 0:
        raise LookupError("No active backend was found")

    choice = easygui.buttonbox(body, title, choices)
    if choice is None:
        raise LookupError("You must choose a backend")

    return choice.split('\n')[0]


def _get_backend_by_name(provider, name: str):
    try:
        return provider.get_backend(name)
    except qiskit.exceptions.QiskitError:
        raise LookupError(f"No such backend name: {name}")


def execute_job(circuit: qiskit.QuantumCircuit, shots: int, *,
                backend_name: Optional[str] = None, skip_simulated: bool = True,
                monitor_job: bool = True):
    """
    runs the circuit on an ibm-q computer, and returns the histogram result.

    @param circuit: the quantum circuit to run
    @param shots: times to run
    @param backend_name: the ibm-q backend name; if unspecified, the user is queried with all possible options
    @param skip_simulated: if querying user for a backend name, hide the simulated backends
    @param monitor_job: print an updating job status (queue position)

    @raises LookupError: if can't find backend

    @returns: an active job. you may call get_hist on it
    """
    with PrintTimer('loading account...  '):
        provider = IBMQ.load_account()

    if backend_name is None:
        backend_name = query_backend_name(skip_simulated=skip_simulated)
    backend = _get_backend_by_name(provider, backend_name)

    with PrintTimer('sending job...      '):
        job = qiskit.execute(circuit, backend=backend, shots=shots)

    if monitor_job:
        job_monitor(job)

    return job


def get_hist(job) -> Dict[str, int]:
    """
    returns the histogram of the job's results

    @param job: an active job

    @return: results histogram, i.e. {"001": 2, "010": 13, "111": 985}
    """
    return dict(job.result().get_counts())
