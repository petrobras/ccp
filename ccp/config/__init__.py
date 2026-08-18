POLYTROPIC_METHOD = "sandberg_colby"
EOS = "REFPROP"

# Multiprocessing controls, read at pool-creation time (see ccp/parallel.py).
# The CCP_PARALLEL and CCP_POOL_SIZE environment variables take precedence.
PARALLEL = True  # set to False to run every ccp calculation serially
POOL_SIZE = None  # worker processes per pool; None means one per CPU
