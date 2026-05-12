# TryHackMe Writeups

Данный репозиторий содержит мои walkthrough/writeup-отчёты по задачам с платформы [TryHackMe](https://tryhackme.com/).

Основная цель репозитория:
- практика penetration testing;
- изучение техник повышения привилегий;
- развитие навыков разведки и пост-эксплуатации;
- документирование процесса решения задач;
- ведение собственной базы знаний.

---

## Профиль TryHackMe

https://tryhackme.com/p/moiseyevanton666

---

## Решённые комнаты

| Комната | Уровень | Описание | Ссылка |
|---|---|---|---|
| Break Out The Cage | ![Easy](https://img.shields.io/badge/Easy-Green?style=for-the-badge) | Комната с криптоанализом, эксплуатацией writable-скриптов и повышением привилегий через reverse shell | [Открыть](./BreakOutTheCage/) |
| GamingServer | ![Easy](https://img.shields.io/badge/Easy-Green?style=for-the-badge) | Комната с анализом веб-приложения, поиском hidden directories, расшифровкой RSA-ключа и эксплуатацией уязвимости ядра CVE-2021-3493 (OverlayFS) | [Открыть](./GamingServer/) |
| Bounty Hacker | ![Easy](https://img.shields.io/badge/Easy-Green?style=for-the-badge) | Комната с анонимным FTP, брутфорсом SSH через `hydra` и повышением привилегий через `sudo tar` (GTFOBins) | [Открыть](./BountyHacker/) |
| Zeno | ![Medium](https://img.shields.io/badge/Medium-orange?style=for-the-badge) | Комната с поиском скрытого HTTP-порта, эксплуатацией RCE в Restaurant Management System, утечкой учётных данных в fstab и повышением привилегий через writable systemd unit | [Открыть](./Zeno/) |
| Valley | ![Easy](https://img.shields.io/badge/Easy-Green?style=for-the-badge) | Комната с анализом pcapng-файлов в Wireshark, хардкодом учётных данных в JS, расшифровкой хешей и повышением привилегий через отравление Python-библиотеки (cron) | [Открыть](./Valley/) |

---

## Структура writeup

Каждая папка содержит:
- подробное пошаговое решение;
- используемые команды;
- объяснение действий;
- скриншоты;
- процесс эксплуатации и повышения привилегий;
- найденные флаги (при необходимости скрытые).

---

Автор: **masquadd**