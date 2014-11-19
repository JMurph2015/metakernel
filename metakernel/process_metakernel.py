from __future__ import absolute_import
from metakernel import MetaKernel
from metakernel.pyexpect import REPLWrapper, EOF, u
from subprocess import check_output
import os
import re

__version__ = '0.0'

version_pat = re.compile(r'version (\d+(\.\d+)+)')


class ProcessMetaKernel(MetaKernel):
    implementation = 'process_kernel'
    implementation_version = __version__
    language = 'process'
    language_info = {
        # 'mimetype': 'text/x-python',
        # 'language': 'python',
        # ------ If different from 'language':
        # 'codemirror_mode': 'language',
        # 'pygments_lexer': 'language',
        # 'file_extension': 'py',
    }

    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = "Process"

    @property
    def banner(self):
        return self._banner

    def __init__(self, **kwargs):
        MetaKernel.__init__(self, **kwargs)
        self.wrapper = None
        self.repr = str
        self._start()

    def _start(self):
        if not self.wrapper is None:
            self.wrapper.child.terminate()
        self.wrapper = self.makeWrapper()

    def do_execute_direct(self, code):

        self.payload = []

        if not code.strip():
            self.kernel_resp = {'status': 'ok',
                            'execution_count': self.execution_count,
                            'payload': [], 'user_expressions': {}}
            return

        interrupted = False
        try:
            output = self.wrapper.run_command(code.rstrip(), timeout=None)
        except KeyboardInterrupt:
            self.wrapper.child.sendintr()
            interrupted = True
            self.wrapper._expect_prompt()
            output = self.wrapper.child.before
        except EOF:
            output = self.wrapper.child.before + 'Restarting'
            self._start()

        if interrupted:
            self.kernel_resp = {'status': 'abort',
                            'execution_count': self.execution_count}

        exitcode, trace = self.check_exitcode()

        if exitcode:
            self.kernel_resp = {'status': 'error',
                            'execution_count': self.execution_count,
                            'ename': '', 'evalue': str(exitcode),
                            'traceback': trace}
        else:
            self.kernel_resp = {'status': 'ok',
                            'execution_count': self.execution_count,
                            'payload': [], 'user_expressions': {}}

        return output

    def check_exitcode(self):
        """
        Return (1, ["trace"]) if error.
        """
        return (0, None)

    def makeWrapper(self):
        raise NotImplementedError


class BashKernel(ProcessMetaKernel):
    # Identifiers:
    implementation = 'bash_kernel'
    language = 'bash'
    language_info = {
        'mimetype': 'text/x-bash',
        'language': 'bash',
        # ------ If different from 'language':
        # 'codemirror_mode': 'language',
        # 'pygments_lexer': 'language',
        'file_extension': 'sh',
    }

    _banner = None
    @property
    def banner(self):
        if self._banner is None:
            self._banner = check_output(['bash', '--version']).decode('utf-8')
        return self._banner

    def makeWrapper(self):
        """Start a bash shell and return a :class:`REPLWrapper` object.

        Note that this is equivalent :function:`metakernel.pyexpect.bash`,
        but is used here as an example of how to be cross-platform.
        """
        if os.name == 'nt':
            command = 'bash'
            orig_prompt = '__repl_ready__'
            prompt_cmd = 'echo __repl_ready__'
            prompt_change = None

        else:
            command = 'bash -i'
            prompt_change = u("PS1='{0}' PS2='{1}' PROMPT_COMMAND=''")
            prompt_cmd = None
            orig_prompt = re.compile('[$#]')

        extra_init_cmd = "export PAGER=cat"

        return REPLWrapper(command, orig_prompt, prompt_change,
                           prompt_cmd=prompt_cmd,
                           extra_init_cmd=extra_init_cmd)

if __name__ == '__main__':
    from IPython.kernel.zmq.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=BashKernel)
