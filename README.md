### pyptimerobot

##### Config

Put a configfile in `configs` for each monitored uri

A config may look like this:

```json
{
  "name": "MyName",
  "url": "https://www.python.org"
}
```
* `name` is mandatory
* `url` is mandatory


##### Installation
```bash
git clone https://github.com/holgersielaff/pyptimerobot
cd pytimerobot
python3 -m venv venv
./venv/bin/python3 -m pip install -r requirements.txt
```

##### Run the script

```bash
./venv/bin/python3 robot.py
```

##### Why Flask?

To build a web frontend later :)
