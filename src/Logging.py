import os
import yaml
import logging.config
import logging.handlers

def setupLogging():
    configFile = os.path.join("loggingConfigs", "config.yaml")
    with open(configFile) as fIn:
        config = yaml.safe_load(fIn)
    logging.config.dictConfig(config)

    logger = logging.getLogger("V3RS")
    logging.basicConfig(level="INFO")
    logger.info("Logger ready")

    pil_logger = logging.getLogger('PIL')
    pil_logger.setLevel(logging.INFO)

    return logger