"""Testes unitários para os repositórios assíncronos do PostgreSQL na geocoding-api."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import GeocodingCache, ReverseGeocodingCache
from src.database.repositories import (
    GeocodingRepository,
    ReverseGeocodingRepository,
    normalize_address,
)


def test_normalize_address():
    """Valida a padronização e remoção de espaços redundantes e conversão para minúsculas."""
    raw = "   Avenida   Anhanguera,   Setor Central  "
    expected = "avenida anhanguera, setor central"
    assert normalize_address(raw) == expected


# ==============================================================================
# GeocodingRepository Tests
# ==============================================================================


def test_geocoding_repository_get_found(mock_db_session: AsyncMock):
    """Testa busca unitária no cache retornando registro existente."""

    async def _test():
        cached = GeocodingCache(
            address="avenida 85",
            latitude=-16.69,
            longitude=-49.26,
            formatted_address="Avenida 85, Goiânia, GO",
            place_id="1",
        )
        mock_db_session.get.return_value = cached

        repo = GeocodingRepository(mock_db_session)
        result = await repo.get("Avenida 85")

        assert result is cached
        mock_db_session.get.assert_called_once_with(GeocodingCache, "avenida 85")

    asyncio.run(_test())


def test_geocoding_repository_get_error_rolls_back(
    mock_db_session: AsyncMock,
):
    """Testa tratamento de erro de banco com rollback automático na busca unitária."""

    async def _test():
        mock_db_session.get.side_effect = SQLAlchemyError("DB Error")

        repo = GeocodingRepository(mock_db_session)
        with pytest.raises(SQLAlchemyError):
            await repo.get("Rua T-55")

        mock_db_session.rollback.assert_called_once()

    asyncio.run(_test())


def test_geocoding_repository_get_many(mock_db_session: AsyncMock):
    """Testa busca de múltiplos endereços em lote no repositório."""

    async def _test():
        repo = GeocodingRepository(mock_db_session)

        # Lista vazia retorna dicionário vazio
        empty_result = await repo.get_many([])
        assert empty_result == {}

        # Com endereços
        c1 = GeocodingCache(
            address="rua 1",
            latitude=-16.1,
            longitude=-49.1,
            formatted_address="Rua 1",
            place_id="1",
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [c1]
        mock_db_session.execute.return_value = mock_result

        res = await repo.get_many(["Rua 1"])
        assert "rua 1" in res
        assert res["rua 1"] == c1

    asyncio.run(_test())


def test_geocoding_repository_get_many_error(mock_db_session: AsyncMock):
    """Garante rollback caso a busca em lote falhe."""

    async def _test():
        mock_db_session.execute.side_effect = SQLAlchemyError("Error")
        repo = GeocodingRepository(mock_db_session)

        with pytest.raises(SQLAlchemyError):
            await repo.get_many(["Rua 1"])

        mock_db_session.rollback.assert_called_once()

    asyncio.run(_test())


def test_geocoding_repository_add_and_add_many(
    mock_db_session: AsyncMock,
):
    """Testa inserção e upsert unitário e em lote com commit e flush."""

    async def _test():
        repo = GeocodingRepository(mock_db_session)

        # Adicionar lista vazia
        await repo.add_many([])
        assert mock_db_session.execute.call_count == 0

        item = GeocodingCache(
            address="Avenida T-63",
            latitude=-16.71,
            longitude=-49.27,
            formatted_address="Avenida T-63, Goiânia, GO",
            place_id="2",
        )

        # Inserção com auto_commit=True
        await repo.add(item, auto_commit=True)
        assert mock_db_session.execute.call_count == 1
        assert mock_db_session.commit.call_count == 1

        # Inserção com auto_commit=False (flush)
        await repo.add_many([item], auto_commit=False)
        assert mock_db_session.flush.call_count == 1

    asyncio.run(_test())


def test_geocoding_repository_add_many_error(mock_db_session: AsyncMock):
    """Valida rollback quando a gravação em lote de geocodificação direta falha."""

    async def _test():
        mock_db_session.execute.side_effect = SQLAlchemyError("Error")
        repo = GeocodingRepository(mock_db_session)
        item = GeocodingCache(
            address="Rua X",
            latitude=0.0,
            longitude=0.0,
            formatted_address="X",
            place_id="1",
        )

        with pytest.raises(SQLAlchemyError):
            await repo.add_many([item], auto_commit=True)

        mock_db_session.rollback.assert_called_once()

    asyncio.run(_test())


# ==============================================================================
# ReverseGeocodingRepository Tests
# ==============================================================================


def test_reverse_geocoding_repository_get(mock_db_session: AsyncMock):
    """Testa busca unitária de geocodificação reversa."""

    async def _test():
        cached = ReverseGeocodingCache(
            coord_key="-16.68000,-49.25000",
            latitude=-16.68,
            longitude=-49.25,
            raw_data_json='{"road": "Avenida Anhanguera"}',
        )
        mock_db_session.get.return_value = cached

        repo = ReverseGeocodingRepository(mock_db_session)
        res = await repo.get(-16.68, -49.25)
        assert res is cached

    asyncio.run(_test())


def test_reverse_geocoding_repository_get_error(
    mock_db_session: AsyncMock,
):
    """Testa rollback em falha de consulta de reverse geocoding."""

    async def _test():
        mock_db_session.get.side_effect = SQLAlchemyError("Error")
        repo = ReverseGeocodingRepository(mock_db_session)

        with pytest.raises(SQLAlchemyError):
            await repo.get(-16.68, -49.25)

        mock_db_session.rollback.assert_called_once()

    asyncio.run(_test())


def test_reverse_geocoding_repository_get_many(
    mock_db_session: AsyncMock,
):
    """Testa busca em lote de geocodificação reversa."""

    async def _test():
        repo = ReverseGeocodingRepository(mock_db_session)

        # Vazio
        assert await repo.get_many([]) == {}

        # Com coordenadas
        cached = ReverseGeocodingCache(
            coord_key="-16.68000,-49.25000",
            latitude=-16.68,
            longitude=-49.25,
            raw_data_json='{"road": "Avenida Anhanguera"}',
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [cached]
        mock_db_session.execute.return_value = mock_result

        res = await repo.get_many([(-16.68, -49.25)])
        assert "-16.68000,-49.25000" in res

    asyncio.run(_test())


def test_reverse_geocoding_repository_get_many_error(
    mock_db_session: AsyncMock,
):
    """Testa rollback em erro de busca em lote reverse."""

    async def _test():
        mock_db_session.execute.side_effect = SQLAlchemyError("Error")
        repo = ReverseGeocodingRepository(mock_db_session)

        with pytest.raises(SQLAlchemyError):
            await repo.get_many([(-16.68, -49.25)])

        mock_db_session.rollback.assert_called_once()

    asyncio.run(_test())


def test_reverse_geocoding_repository_add_and_add_many(
    mock_db_session: AsyncMock,
):
    """Testa inserção e upsert em lote para reverse geocoding."""

    async def _test():
        repo = ReverseGeocodingRepository(mock_db_session)

        # Vazio retorna direto
        await repo.add_many([])
        assert mock_db_session.execute.call_count == 0

        item = ReverseGeocodingCache(
            coord_key="-16.70000,-49.28000",
            latitude=-16.7,
            longitude=-49.28,
            raw_data_json="{}",
        )

        # auto_commit=True
        await repo.add(item, auto_commit=True)
        assert mock_db_session.execute.call_count == 1
        assert mock_db_session.commit.call_count == 1

        # auto_commit=False (flush)
        await repo.add_many([item], auto_commit=False)
        assert mock_db_session.flush.call_count == 1

    asyncio.run(_test())


def test_reverse_geocoding_repository_add_many_error(
    mock_db_session: AsyncMock,
):
    """Testa rollback em erro ao salvar lote de reverse geocoding."""

    async def _test():
        mock_db_session.execute.side_effect = SQLAlchemyError("Error")
        repo = ReverseGeocodingRepository(mock_db_session)
        item = ReverseGeocodingCache(
            coord_key="-16.70000,-49.28000",
            latitude=-16.7,
            longitude=-49.28,
            raw_data_json="{}",
        )

        with pytest.raises(SQLAlchemyError):
            await repo.add_many([item], auto_commit=True)

        mock_db_session.rollback.assert_called_once()

    asyncio.run(_test())
