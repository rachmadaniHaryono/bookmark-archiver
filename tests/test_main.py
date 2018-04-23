import os
import subprocess

import pytest


@pytest.mark.parametrize("use_subprocesss", [True, False])
def test_help(capsys, use_subprocesss):
    conf_filename = 'archive.conf'
    assert not os.path.isfile(conf_filename)
    os.environ['BOOKMARK_ARCHIVER_USE_DEFAULT_CONFIG'] = '1'
    if use_subprocesss:
        exit_code, output = subprocess.getstatusoutput(["archive", "--help"])
        assert exit_code == 0
        assert output
    else:
        with pytest.raises(SystemExit):
            from bookmark_archiver import archive
            archive.main('archive', '--help')
        out, err = capsys.readouterr()
        assert out
        assert err == ''
    os.environ['BOOKMARK_ARCHIVER_USE_DEFAULT_CONFIG'] = ''

