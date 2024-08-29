# PICNIC

## Run PICNIC in docker (easiest)

You need to have docker installed already, then you can download the docker
image and run it on your data. The major benefit of docker is that
Python, FSL, FreeSurfer, AFNI, Connectome Workbench, and PICNIC are
already installed inside the docker container, so you don't have to
deal with those dependencies on your own.

```bash
docker pull mfschmidt/picnic:latest
docker run --rm \
-v /path/to/your/data:/input:ro \
-v /path/to/your/results:/output:rw \
-v /path/to/your/input_deck.txt:/input_deck.txt:ro \
mfschmidt/picnic:latest /input /output
```

## Run PICNIC directly

To run picnic directly, you don't need docker, but you do need to have all of
its dependencies already installed.

```bash
pip install -U git+git@github.com:ehauser-mind/PICNIC.git
cd PICNIC
./nipybipy/run.py my_input_deck.inp
```

and stuff

