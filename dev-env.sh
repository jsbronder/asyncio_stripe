#!/usr/bin/env bash

cleanup() {
	[ -n "${bashrc}" ] && rm -f "${bashrc}"
}

trap cleanup HUP TERM

topdir=$(readlink -f $(dirname $0))
bashrc=$(TMPDIR=${topdir} mktemp .devrc-XXXXXX)
PYTHON_VERSION=${PYTHON_VERSION:-3.5}
virtualenv=.virtualenv${PYTHON_VERSION}
make=$(which gmake 2>/dev/null || which make)

${make} -s PYTHON_VERSION=${PYTHON_VERSION} venv -C ${topdir} || exit 1

if [ ! -d ${topdir}/${virtualenv} ]; then
	echo "No virtualenv installed at ${topdir}/${virtualenv}"
	exit 1;
fi

cat > ${bashrc} <<-EOF
	[ -f ~/.bash_profile ] && source ~/.bash_profile
	source ${topdir}/${virtualenv}/bin/activate
EOF

if [ -z "$*" ]; then
	/usr/bin/env bash --rcfile ${bashrc} -i
else
	source ${bashrc}
	$*
fi

rm -f ${bashrc}

# vim: noet
