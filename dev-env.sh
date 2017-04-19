#!/usr/bin/env bash

cleanup() {
	[ -n "${bashrc}" ] && rm -f "${bashrc}"
}

trap cleanup HUP TERM

topdir=$(readlink -f $(dirname $0))
package=asyncio_stripe
bashrc=$(TMPDIR=${topdir} mktemp .devrc-XXXXXX)
PYTHON_VERSION=${PYTHON_VERSION:-3.5}
virtualenv=$(readlink -f ${VIRTUAL_ENV:-${topdir}/virtualenv${PYTHON_VERSION}})
venv_devdir=${virtualenv}/${package}-dev
make=$(which gmake 2>/dev/null || which make)

if [ ! -d ${virtualenv} ]; then
	virtualenv --python=python${PYTHON_VERSION} ${virtualenv} || exit 1
fi

if [ ! -d ${venv_devdir} ]; then
	mkdir -p ${venv_devdir}
fi

for reqf in "requirements.txt" "requirements-test.txt"; do
	if [ ${venv_devdir}/${reqf} -ot ${reqf} ]; then
		(source ${virtualenv}/bin/activate && pip install -r ${reqf})
		touch -m ${venv_devdir}/${reqf}
	fi
done

cat > ${bashrc} <<-EOF
	[ -f ~/.bash_profile ] && source ~/.bash_profile
	source ${virtualenv}/bin/activate
EOF

if [ -z "$*" ]; then
	/usr/bin/env bash --rcfile ${bashrc} -i
else
	source ${bashrc}
	$*
fi

rm -f ${bashrc}

# vim: noet
