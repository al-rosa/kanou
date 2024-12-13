import logging

import colorlog


def setup_logger():
    """カラーロギングの設定"""
    # すでにハンドラが設定されている場合は新しいロガーを作成しない
    logger = logging.getLogger()
    if logger.handlers:
        return logger

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(message)s',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        }
    ))

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
