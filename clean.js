const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function clean() {
    const users = await prisma.user.findMany({
        where: { role: 'STUDENT' },
        include: { student: true }
    });

    for (const u of users) {
        if (!u.student) {
            console.log('Deleting orphaned user:', u.email);
            await prisma.user.delete({ where: { id: u.id } });
        }
    }
}

clean().then(() => prisma.$disconnect()).catch(console.error);
