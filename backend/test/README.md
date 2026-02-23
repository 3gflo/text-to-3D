## Running Tests

### Setup
Before running the tests for the first time, you must install the package in "editable" mode. From the project root, run:

```bash
  
```

### Result
You will see a directory called google_sheets_integration.egg-info appear. This is intended and will be ignored by git


## Testing 3D Generation Pipeline

### Setup
You must install all dependencies before starting the local web server via run.py.
run.py must be executed from its directory (backend/).

### Generating
To generate a 3D model, modify the PROMPT, IMAGE_SERVICE, and THREED_SERVICE parameters in test_3Dgen.py.
In a new terminal with the same dependencies, execute test_3Dgen.py. 
