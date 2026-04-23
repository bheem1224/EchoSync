//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, ee = () => {};
function te(e) {
	return e();
}
function ne(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function re() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var v = 1024, y = 2048, b = 4096, ie = 8192, ae = 16384, oe = 32768, se = 1 << 25, ce = 65536, le = 1 << 19, ue = 1 << 20, de = 65536, fe = 1 << 21, pe = 1 << 22, me = 1 << 23, he = Symbol("$state"), ge = Symbol("legacy props"), _e = Symbol(""), x = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), ve = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function ye(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function be() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function xe(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Se() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ce(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function we() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Te() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ee(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function De() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Oe() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function ke() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ae() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function je() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Me(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ne() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var S = !1;
function Pe(e) {
	S = e;
}
var C;
function w(e) {
	if (e === null) throw Me(), r;
	return C = e;
}
function Fe() {
	return w(/* @__PURE__ */ I(C));
}
function T(e) {
	if (S) {
		if (/* @__PURE__ */ I(C) !== null) throw Me(), r;
		C = e;
	}
}
function Ie(e = 1) {
	if (S) {
		for (var t = e, n = C; t--;) n = /* @__PURE__ */ I(n);
		C = n;
	}
}
function Le(e = !0) {
	for (var t = 0, n = C;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ I(n);
		e && n.remove(), n = i;
	}
}
function Re(e) {
	if (!e || e.nodeType !== 8) throw Me(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function ze(e) {
	return e === this.v;
}
function Be(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ve(e) {
	return !Be(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var E = null;
function He(e) {
	E = e;
}
function Ue(e, n = !1, r) {
	E = {
		p: E,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: K,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function We(e) {
	var t = E, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) pn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, E = t.p, e ?? {};
}
function Ge() {
	return !t || E !== null && E.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ke = [];
function qe() {
	var e = Ke;
	Ke = [], ne(e);
}
function D(e) {
	if (Ke.length === 0 && !ot) {
		var t = Ke;
		queueMicrotask(() => {
			t === Ke && qe();
		});
	}
	Ke.push(e);
}
function Je() {
	for (; Ke.length > 0;) qe();
}
function Ye(e) {
	var t = K;
	if (t === null) return U.f |= me, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Xe(e, t);
}
function Xe(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var Ze = ~(y | b | v);
function O(e, t) {
	e.f = e.f & Ze | t;
}
function Qe(e) {
	e.f & 512 || e.deps === null ? O(e, v) : O(e, b);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function $e(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= de, $e(t.deps));
}
function et(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), $e(e.deps), O(e, v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var tt = !1, nt = !1;
function rt(e) {
	var t = nt;
	try {
		return nt = !1, [e(), nt];
	} finally {
		nt = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var k = /* @__PURE__ */ new Set(), A = null, it = null, j = null, at = null, ot = !1, st = !1, ct = null, lt = null, ut = 0, dt = 1, ft = class t {
	id = dt++;
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Map();
	#i = /* @__PURE__ */ new Map();
	#a = null;
	#o = [];
	#s = [];
	#c = /* @__PURE__ */ new Set();
	#l = /* @__PURE__ */ new Set();
	#u = /* @__PURE__ */ new Map();
	#d = /* @__PURE__ */ new Set();
	is_fork = !1;
	#f = !1;
	#p = /* @__PURE__ */ new Set();
	#m() {
		return this.is_fork || this.#i.size > 0;
	}
	#h() {
		for (let n of this.#p) for (let r of n.#i.keys()) {
			for (var e = !1, t = r; t.parent !== null;) {
				if (this.#u.has(t)) {
					e = !0;
					break;
				}
				t = t.parent;
			}
			if (!e) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#u.has(e) || this.#u.set(e, {
			d: [],
			m: []
		}), this.#d.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#u.get(e);
		if (n) {
			this.#u.delete(e);
			for (var r of n.d) O(r, y), t(r);
			for (r of n.m) O(r, b), t(r);
		}
		this.#d.add(e);
	}
	#g() {
		if (ut++ > 1e3 && (k.delete(this), mt()), !this.#m()) {
			for (let e of this.#c) this.#l.delete(e), O(e, y), this.schedule(e);
			for (let e of this.#l) O(e, b), this.schedule(e);
		}
		let n = this.#o;
		this.#o = [], this.apply();
		var r = ct = [], i = [], a = lt = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw bt(e), t;
		}
		if (A = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (ct = null, lt = null, this.#m() || this.#h()) {
			this.#v(i), this.#v(r);
			for (let [e, t] of this.#u) yt(e, t);
		} else {
			this.#r.size === 0 && k.delete(this), this.#c.clear(), this.#l.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), it = this, ht(i), ht(r), it = null, this.#a?.resolve();
		}
		var s = A;
		if (this.#o.length > 0) {
			let e = s ??= this;
			e.#o.push(...this.#o.filter((t) => !e.#o.includes(t)));
		}
		s !== null && (k.add(s), s.#g()), e && !k.has(this) && this.#y();
	}
	#_(t, n, r) {
		t.f ^= v;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#u.has(i)) && i.fn !== null) {
				o ? i.f ^= v : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Hn(i) && (a & 16 && this.#l.add(i), qn(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#v(e) {
		for (var t = 0; t < e.length; t += 1) et(e[t], this.#c, this.#l);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), j?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		A = this;
	}
	deactivate() {
		A = null, j = null;
	}
	flush() {
		try {
			st = !0, A = this, this.#g();
		} finally {
			ut = 0, at = null, ct = null, lt = null, st = !1, A = null, j = null, Rt.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear(), this.#n.clear(), k.delete(this);
	}
	register_created_effect(e) {
		this.#s.push(e);
	}
	#y() {
		for (let l of k) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			var r = [...l.current.keys()].filter((e) => !this.current.has(e));
			if (r.length === 0) e && l.discard();
			else if (t.length > 0) {
				if (e) for (let e of this.#d) l.unskip_effect(e, (e) => {
					e.f & 4194320 ? l.schedule(e) : l.#v([e]);
				});
				l.activate();
				var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
				for (var o of t) gt(o, r, i, a);
				a = /* @__PURE__ */ new Map();
				var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e : !0);
				for (let e of this.#s) !(e.f & 155648) && _t(e, s, a) && (e.f & 4194320 ? (O(e, y), l.schedule(e)) : l.#c.add(e));
				if (l.#o.length > 0) {
					l.apply();
					for (var c of l.#o) l.#_(c, [], []);
					l.#o = [];
				}
				l.deactivate();
			}
		}
		for (let e of k) e.#p.has(this) && (e.#p.delete(this), e.#p.size === 0 && !e.#m() && (e.activate(), e.#g()));
	}
	increment(e, t) {
		let n = this.#r.get(t) ?? 0;
		if (this.#r.set(t, n + 1), e) {
			let e = this.#i.get(t) ?? 0;
			this.#i.set(t, e + 1);
		}
	}
	decrement(e, t, n) {
		let r = this.#r.get(t) ?? 0;
		if (r === 1 ? this.#r.delete(t) : this.#r.set(t, r - 1), e) {
			let e = this.#i.get(t) ?? 0;
			e === 1 ? this.#i.delete(t) : this.#i.set(t, e - 1);
		}
		this.#f || n || (this.#f = !0, D(() => {
			this.#f = !1, this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#c.add(t);
		for (let e of t) this.#l.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	on_fork_commit(e) {
		this.#n.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#n) e(this);
		this.#n.clear();
	}
	settled() {
		return (this.#a ??= re()).promise;
	}
	static ensure() {
		if (A === null) {
			let e = A = new t();
			st || (k.add(A), ot || D(() => {
				A === e && e.flush();
			}));
		}
		return A;
	}
	apply() {
		if (!e || !this.is_fork && k.size === 1) {
			j = null;
			return;
		}
		j = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) j.set(e, t);
		for (let e of k) if (!(e === this || e.is_fork)) {
			var t = !1, n = !1;
			if (e.id < this.id) for (let [r, [, i]] of e.current) i || (t ||= this.current.has(r), n ||= !this.current.has(r));
			if (t && n) this.#p.add(e);
			else for (let [t, n] of e.previous) j.has(t) || j.set(t, n);
		}
	}
	schedule(t) {
		if (at = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (ct !== null && n === K && (e || (U === null || !(U.f & 2)) && !tt)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= v;
			}
		}
		this.#o.push(n);
	}
};
function pt(e) {
	var t = ot;
	ot = !0;
	try {
		var n;
		for (e && (A !== null && !A.is_fork && A.flush(), n = e());;) {
			if (Je(), A === null) return n;
			A.flush();
		}
	} finally {
		ot = t;
	}
}
function mt() {
	try {
		we();
	} catch (e) {
		Xe(e, at);
	}
}
var M = null;
function ht(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Hn(r) && (M = /* @__PURE__ */ new Set(), qn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && En(r), M?.size > 0)) {
				Rt.clear();
				for (let e of M) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) M.has(n) && (M.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || qn(n);
					}
				}
				M.clear();
			}
		}
		M = null;
	}
}
function gt(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? gt(i, t, n, r) : e & 4194320 && !(e & 2048) && _t(i, t, r) && (O(i, y), vt(i));
	}
}
function _t(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && _t(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function vt(e) {
	A.schedule(e);
}
function yt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), O(e, v);
		for (var n = e.first; n !== null;) yt(n, t), n = n.next;
	}
}
function bt(e) {
	O(e, v);
	for (var t = e.first; t !== null;) bt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function xt(e) {
	let t = 0, n = Bt(0), r;
	return () => {
		un() && (Q(n), yn(() => (t === 0 && (r = Zn(() => e(() => Ut(n)))), t += 1, () => {
			D(() => {
				--t, t === 0 && (r?.(), r = void 0, Ut(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var St = ce | le;
function Ct(e, t, n, r) {
	new wt(e, t, n, r);
}
var wt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = S ? C : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = xt(() => (this.#m = Bt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = K;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = K.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = xn(() => {
			if (S) {
				let e = this.#t;
				Fe();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, St), S && (this.#e = C);
	}
	#g() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = B(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), D(() => {
			var e = this.#c = document.createDocumentFragment(), t = Zt();
			e.append(t), this.#a = this.#x(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Dn(this.#o, () => {
				this.#o = null;
			}), this.#b(A));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				jn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#b(A);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		et(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = K, n = U, r = E;
		q(this.#i), G(this.#i), He(this.#i.ctx);
		try {
			return ft.ensure(), e();
		} catch (e) {
			return Ye(e), null;
		} finally {
			q(t), G(n), He(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Dn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, D(() => {
			this.#d = !1, this.#m && Vt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Q(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		A?.is_fork ? (this.#a && A.skip_effect(this.#a), this.#o && A.skip_effect(this.#o), this.#s && A.skip_effect(this.#s), A.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), S && (w(this.#t), Ie(), w(Le()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Ne();
				return;
			}
			r = !0, i && Ae(), this.#s !== null && Dn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Xe(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var t = K;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Xe(e, this.#i.parent), null;
				}
			}));
		};
		D(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Xe(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Xe(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Tt(e, t, n, r) {
	let i = Ge() ? kt : jt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = K, s = Et(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		s();
		try {
			r(e);
		} catch (e) {
			o.f & 16384 || Xe(e, o);
		}
		Dt();
	}
	if (n.length === 0) {
		c.then(() => l(t.map(i)));
		return;
	}
	var u = Ot();
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ At(e))).then((e) => l([...t.map(i), ...e])).catch((e) => Xe(e, o)).finally(() => u());
	}
	c ? c.then(() => {
		s(), d(), Dt();
	}) : d();
}
function Et() {
	var e = K, t = U, n = E, r = A;
	return function(i = !0) {
		q(e), G(t), He(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Dt(e = !0) {
	q(null), G(null), He(null), e && A?.deactivate();
}
function Ot() {
	var e = K, t = e.b, n = A, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function kt(e) {
	var t = 2 | y;
	return K !== null && (K.f |= le), {
		ctx: E,
		deps: null,
		effects: null,
		equals: ze,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: K,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function At(e, t, n) {
	let r = K;
	r === null && be();
	var a = void 0, o = Bt(i), s = !U, c = /* @__PURE__ */ new Map();
	return vn(() => {
		var t = K, n = re();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, n.reject).finally(Dt);
		} catch (e) {
			n.reject(e), Dt();
		}
		var i = A;
		if (s) {
			if (t.f & 32768) var l = Ot();
			if (r.b.is_rendered()) c.get(i)?.reject(x), c.delete(i);
			else {
				for (let e of c.values()) e.reject(x);
				c.clear();
			}
			c.set(i, n);
		}
		let u = (e, n = void 0) => {
			if (l && l(n === x), !(n === x || t.f & 16384)) {
				if (i.activate(), n) o.f |= me, Vt(o, n);
				else {
					o.f & 8388608 && (o.f ^= me), Vt(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(x);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), dn(() => {
		for (let e of c.values()) e.reject(x);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function jt(e) {
	let t = /* @__PURE__ */ kt(e);
	return t.equals = Ve, t;
}
function Mt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Nt(e) {
	var t, n = K, r = e.parent;
	if (!H && r !== null && r.f & 24576) return je(), e.v;
	q(r);
	try {
		e.f &= ~de, Mt(e), t = Wn(e);
	} finally {
		q(n);
	}
	return t;
}
function Pt(e) {
	var t = Nt(e);
	if (!e.equals(t) && (e.wv = Vn(), (!A?.is_fork || e.deps === null) && (A === null ? e.v = t : A.capture(e, t, !0), e.deps === null))) {
		O(e, v);
		return;
	}
	H || (j === null ? Qe(e) : (un() || A?.is_fork) && j.set(e, t));
}
function Ft(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(x), t.teardown = ee, t.ac = null, Kn(t, 0), Cn(t));
}
function It(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && qn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Lt = /* @__PURE__ */ new Set(), Rt = /* @__PURE__ */ new Map(), zt = !1;
function Bt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: ze,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function N(e, t) {
	let n = Bt(e, t);
	return Fn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, n = !1, r = !0) {
	let i = Bt(e);
	return n || (i.equals = Ve), t && r && E !== null && E.l !== null && (E.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return U !== null && (!W || U.f & 131072) && Ge() && U.f & 4325394 && (J === null || !c.call(J, e)) && ke(), Vt(e, n ? Gt(t) : t, lt);
}
function Vt(e, t, n = null) {
	if (!e.equals(t)) {
		Rt.set(e, H ? t : e.v);
		var r = ft.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Nt(t), j === null && Qe(t);
		}
		e.wv = Vn(), Wt(e, y, n), Ge() && K !== null && K.f & 1024 && !(K.f & 96) && (Z === null ? In([e]) : Z.push(e)), !r.is_fork && Lt.size > 0 && !zt && Ht();
	}
	return t;
}
function Ht() {
	zt = !1;
	for (let e of Lt) e.f & 1024 && O(e, b), Hn(e) && qn(e);
	Lt.clear();
}
function Ut(e) {
	F(e, e.v + 1);
}
function Wt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ge(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === K)) {
			var l = (c & y) === 0;
			if (l && O(s, t), c & 2) {
				var u = s;
				j?.delete(u), c & 65536 || (c & 512 && (s.f |= de), Wt(u, b, n));
			} else if (l) {
				var d = s;
				c & 16 && M !== null && M.add(d), n === null ? vt(d) : n.push(d);
			}
		}
	}
}
function Gt(e) {
	if (typeof e != "object" || !e || he in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ N(0), s = null, c = zn, l = (e) => {
		if (zn === c) return e();
		var t = U, n = zn;
		G(null), Bn(c);
		var r = e();
		return G(t), Bn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ N(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && De();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ N(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ N(i, s));
					n.set(t, e), Ut(a);
				}
			} else F(r, i), Ut(a);
			return !0;
		},
		get(t, r, a) {
			if (r === he) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ N(Gt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Q(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Q(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === he) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || K !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ N(a ? Gt(e[t]) : i, s)), n.set(t, r)), Q(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ N(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ N(void 0, s)), F(u, Gt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Gt(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), ee = Number(t);
					Number.isInteger(ee) && ee >= _.v && F(_, ee + 1);
				}
				Ut(a);
			}
			return !0;
		},
		ownKeys(e) {
			Q(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Oe();
		}
	});
}
var Kt, qt, Jt, Yt;
function Xt() {
	if (Kt === void 0) {
		Kt = window, qt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Jt = f(t, "firstChild").get, Yt = f(t, "nextSibling").get, _(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), _(n) && (n.__t = void 0);
	}
}
function Zt(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function Qt(e) {
	return Jt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function I(e) {
	return Yt.call(e);
}
function L(e, t) {
	if (!S) return /* @__PURE__ */ Qt(e);
	var n = /* @__PURE__ */ Qt(C);
	if (n === null) n = C.appendChild(Zt());
	else if (t && n.nodeType !== 3) {
		var r = Zt();
		return n?.before(r), w(r), r;
	}
	return t && nn(n), w(n), n;
}
function R(e, t = 1, n = !1) {
	let r = S ? C : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ I(r);
	if (!S) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = Zt();
			return r === null ? i?.after(a) : r.before(a), w(a), a;
		}
		nn(r);
	}
	return w(r), r;
}
function $t(e) {
	e.textContent = "";
}
function en() {
	return !e || M !== null ? !1 : (K.f & oe) !== 0;
}
function tn(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function nn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var rn = !1;
function an() {
	rn || (rn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function on(e) {
	var t = U, n = K;
	G(null), q(null);
	try {
		return e();
	} finally {
		G(t), q(n);
	}
}
function sn(e, t, n, r = n) {
	e.addEventListener(t, () => on(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), an();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function cn(e) {
	K === null && (U === null && Ce(e), Se()), H && xe(e);
}
function ln(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = K;
	n !== null && n.f & 8192 && (e |= ie);
	var r = {
		ctx: E,
		deps: null,
		nodes: null,
		f: e | y | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	A?.register_created_effect(r);
	var i = r;
	if (e & 4) ct === null ? ft.ensure().schedule(r) : ct.push(r);
	else if (t !== null) {
		try {
			qn(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ce));
	}
	if (i !== null && (i.parent = n, n !== null && ln(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function un() {
	return U !== null && !W;
}
function dn(e) {
	let t = z(8, null);
	return O(t, v), t.teardown = e, t;
}
function fn(e) {
	cn("$effect");
	var t = K.f;
	if (!U && t & 32 && !(t & 32768)) {
		var n = E;
		(n.e ??= []).push(e);
	} else return pn(e);
}
function pn(e) {
	return z(4 | ue, e);
}
function mn(e) {
	return cn("$effect.pre"), z(8 | ue, e);
}
function hn(e) {
	ft.ensure();
	let t = z(64 | le, e);
	return () => {
		V(t);
	};
}
function gn(e) {
	ft.ensure();
	let t = z(64 | le, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Dn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function _n(e) {
	return z(4, e);
}
function vn(e) {
	return z(pe | le, e);
}
function yn(e, t = 0) {
	return z(8 | t, e);
}
function bn(e, t = [], n = [], r = []) {
	Tt(r, t, n, (t) => {
		z(8, () => e(...t.map(Q)));
	});
}
function xn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | le, e);
}
function Sn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = H, n = U;
		Pn(!0), G(null);
		try {
			t.call(null);
		} finally {
			Pn(e), G(n);
		}
	}
}
function Cn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && on(() => {
			e.abort(x);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function wn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Tn(e.nodes.start, e.nodes.end), n = !0), O(e, se), Cn(e, t && !n), Kn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Sn(e), e.f ^= se, e.f |= ae;
	var i = e.parent;
	i !== null && i.first !== null && En(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Tn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ I(e);
		e.remove(), e = n;
	}
}
function En(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Dn(e, t, n = !0) {
	var r = [];
	On(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function On(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ie;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				On(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function kn(e) {
	An(e, !0);
}
function An(e, t) {
	if (e.f & 8192) {
		e.f ^= ie, e.f & 1024 || (O(e, y), ft.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			An(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function jn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ I(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Mn = null, Nn = !1, H = !1;
function Pn(e) {
	H = e;
}
var U = null, W = !1;
function G(e) {
	U = e;
}
var K = null;
function q(e) {
	K = e;
}
var J = null;
function Fn(t) {
	U !== null && (!e || U.f & 2) && (J === null ? J = [t] : J.push(t));
}
var Y = null, X = 0, Z = null;
function In(e) {
	Z = e;
}
var Ln = 1, Rn = 0, zn = Rn;
function Bn(e) {
	zn = e;
}
function Vn() {
	return ++Ln;
}
function Hn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~de), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Hn(a) && Pt(a), a.wv > e.wv) return !0;
		}
		t & 512 && j === null && O(e, v);
	}
	return !1;
}
function Un(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && J !== null && c.call(J, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Un(o, n, !1) : n === o && (r ? O(o, y) : o.f & 1024 && O(o, b), vt(o));
	}
}
function Wn(e) {
	var t = Y, n = X, r = Z, i = U, a = J, o = E, s = W, c = zn, l = e.f;
	Y = null, X = 0, Z = null, U = l & 96 ? null : e, J = null, He(e.ctx), W = !1, zn = ++Rn, e.ac !== null && (on(() => {
		e.ac.abort(x);
	}), e.ac = null);
	try {
		e.f |= fe;
		var u = e.fn, d = u();
		e.f |= oe;
		var f = e.deps, p = A?.is_fork;
		if (Y !== null) {
			var m;
			if (p || Kn(e, X), f !== null && X > 0) for (f.length = X + Y.length, m = 0; m < Y.length; m++) f[X + m] = Y[m];
			else e.deps = f = Y;
			if (un() && e.f & 512) for (m = X; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && X < f.length && (Kn(e, X), f.length = X);
		if (Ge() && Z !== null && !W && f !== null && !(e.f & 6146)) for (m = 0; m < Z.length; m++) Un(Z[m], e);
		if (i !== null && i !== e) {
			if (Rn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Rn;
			if (t !== null) for (let e of t) e.rv = Rn;
			Z !== null && (r === null ? r = Z : r.push(...Z));
		}
		return e.f & 8388608 && (e.f ^= me), d;
	} catch (e) {
		return Ye(e);
	} finally {
		e.f ^= fe, Y = t, X = n, Z = r, U = i, J = a, He(o), W = s, zn = c;
	}
}
function Gn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (Y === null || !c.call(Y, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~de), o.v !== i && Qe(o), Ft(o), Kn(o, 0);
	}
}
function Kn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Gn(e, n[r]);
}
function qn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		O(e, v);
		var n = K, r = Nn;
		K = e, Nn = !0;
		try {
			t & 16777232 ? wn(e) : Cn(e), Sn(e);
			var i = Wn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Ln;
		} finally {
			Nn = r, K = n;
		}
	}
}
async function Jn() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), pt();
}
function Q(e) {
	var t = (e.f & 2) != 0;
	if (Mn?.add(e), U !== null && !W && !(K !== null && K.f & 16384) && (J === null || !c.call(J, e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < Rn && (e.rv = Rn, Y === null && n !== null && n[X] === e ? X++ : Y === null ? Y = [e] : Y.push(e));
		else {
			(U.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : c.call(r, U) || r.push(U);
		}
	}
	if (H && Rt.has(e)) return Rt.get(e);
	if (t) {
		var i = e;
		if (H) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || Xn(i)) && (a = Nt(i)), Rt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !W && U !== null && (Nn || (U.f & 512) != 0), s = (i.f & oe) === 0;
		Hn(i) && (o && (i.f |= 512), Pt(i)), o && !s && (It(i), Yn(i));
	}
	if (j?.has(e)) return j.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Yn(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (It(t), Yn(t));
}
function Xn(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Rt.has(t) || t.f & 2 && Xn(t)) return !0;
	return !1;
}
function Zn(e) {
	var t = W;
	try {
		return W = !0, e();
	} finally {
		W = t;
	}
}
function Qn(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (he in e) $n(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && he in n && $n(n);
		}
	}
}
function $n(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			$n(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var er = Symbol("events"), tr = /* @__PURE__ */ new Set(), nr = /* @__PURE__ */ new Set();
function rr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || or.call(t, e), !e.cancelBubble) return on(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? D(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function ir(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = rr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && dn(() => {
		t.removeEventListener(e, o, a);
	});
}
var ar = null;
function or(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	ar = e;
	var o = 0, s = ar === e && e[er];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[er] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = U, f = K;
		G(null), q(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[er]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[er] = t, delete e.currentTarget, G(u), q(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var sr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function cr(e) {
	return sr?.createHTML(e) ?? e;
}
function lr(e) {
	var t = tn("template");
	return t.innerHTML = cr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function ur(e, t) {
	var n = K;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function dr(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (S) return ur(C, null), C;
		i === void 0 && (i = lr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Qt(i)));
		var t = r || qt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ Qt(t), s = t.lastChild;
			ur(o, s);
		} else ur(t, t);
		return t;
	};
}
function $(e, t) {
	if (S) {
		var n = K;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = C), Fe();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var fr = ["touchstart", "touchmove"];
function pr(e) {
	return fr.includes(e);
}
function mr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function hr(e, t) {
	return vr(e, t);
}
function gr(e, t) {
	Xt(), t.intro = t.intro ?? !1;
	let n = t.target, i = S, a = C;
	try {
		for (var o = /* @__PURE__ */ Qt(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ I(o);
		if (!o) throw r;
		Pe(!0), w(o);
		let i = vr(e, {
			...t,
			anchor: o
		});
		return Pe(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && Te(), Xt(), $t(n), Pe(!1), hr(e, t);
	} finally {
		Pe(i), w(a);
	}
}
var _r = /* @__PURE__ */ new Map();
function vr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	Xt();
	var u = void 0, d = gn(() => {
		var s = n ?? t.appendChild(Zt());
		Ct(s, { pending: () => {} }, (t) => {
			Ue({});
			var n = E;
			if (o && (n.c = o), a && (i.$$events = a), S && ur(t, null), u = e(t, i) || {}, S && (K.nodes.end = C, C === null || C.nodeType !== 8 || C.data !== "]")) throw Me(), r;
			We();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = pr(r);
					for (let e of [t, document]) {
						var a = _r.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), _r.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, or, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(tr)), nr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = _r.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, or), r.delete(e), r.size === 0 && _r.delete(n)) : r.set(e, i);
			}
			nr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return yr.set(u, d), u;
}
var yr = /* @__PURE__ */ new WeakMap();
function br(e, t) {
	let n = yr.get(e);
	return n ? (yr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var xr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) kn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						jn(r, t), t.append(Zt()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Dn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = A, r = en();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = Zt();
			i.append(a), this.#n.set(e, {
				effect: B(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, B(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else S && (this.anchor = C), this.#a(n);
	}
};
function Sr(e) {
	E === null && ye("onMount"), t && E.l !== null ? Cr(E).m.push(e) : fn(() => {
		let t = Zn(e);
		if (typeof t == "function") return t;
	});
}
function Cr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function wr(e, t, n = !1) {
	var r;
	S && (r = C, Fe());
	var i = new xr(e), a = n ? ce : 0;
	function o(e, t) {
		if (S) {
			var n = Re(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Le();
				w(a), i.anchor = a, Pe(!1), i.ensure(e, t), Pe(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	xn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Tr(e, t) {
	_n(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = tn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Er = Symbol("is custom element"), Dr = Symbol("is html"), Or = ve ? "link" : "LINK";
function kr(e) {
	if (S) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Ar(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Ar(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, D(n), an();
	}
}
function Ar(e, t, n, r) {
	var i = jr(e);
	S && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Or) || i[t] !== (i[t] = n) && (t === "loading" && (e[_e] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Nr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function jr(e) {
	return e.__attributes ??= {
		[Er]: e.nodeName.includes("-"),
		[Dr]: e.namespaceURI === a
	};
}
var Mr = /* @__PURE__ */ new Map();
function Nr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Mr.get(t);
	if (n) return n;
	Mr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Pr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	sn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Fr(t) ? Ir(a) : a, r(a), A !== null && i.add(A), await Jn(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (S && t.defaultValue !== t.value || Zn(n) == null && t.value) && (r(Fr(t) ? Ir(t.value) : t.value), A !== null && i.add(A)), yn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? it : A;
			if (i.has(a)) return;
		}
		Fr(t) && r === Ir(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Fr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Ir(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Lr(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => Qn(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ kt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Q(i);
	}
	n.b.length && mn(() => {
		Rr(t, r), ne(n.b);
	}), fn(() => {
		let e = Zn(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && fn(() => {
		Rr(t, r), ne(n.a);
	});
}
function Rr(e, t) {
	if (e.l.s) for (let t of e.l.s) Q(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function zr(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? Zn(i) : i), c);
	let d;
	if (o) {
		var p = he in e || ge in e;
		d = f(e, n)?.set ?? (p && n in e ? (t) => e[n] = t : void 0);
	}
	var m, h = !1;
	o ? [m, h] = rt(() => e[n]) : m = e[n], m === void 0 && i !== void 0 && (m = u(), d && (a && Ee(n), d(m)));
	var g = a ? () => {
		var t = e[n];
		return t === void 0 ? u() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return g;
	if (d) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || _ || h) && d(t ? g() : e), e) : g();
		});
	}
	var ee = !1, te = (r & 1 ? kt : jt)(() => (ee = !1, g()));
	o && Q(te);
	var ne = K;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Q(te) : a && o ? Gt(e) : e;
			return F(te, n), ee = !0, c !== void 0 && (c = n), e;
		}
		return H && ee || ne.f & 16384 ? te.v : Q(te);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Br(e) {
	return new Vr(e);
}
var Vr = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Q(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === ge ? !0 : (Q(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? gr : hr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && pt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			br(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, Hr;
typeof HTMLElement == "function" && (Hr = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = tn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Wr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Ur(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Br({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = hn(() => {
				yn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Ur(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Ur(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Ur(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Wr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Gr(e, t, n, r, i, a) {
	let o = class extends Hr {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Ur(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region SlskdCard.svelte
var Kr = /* @__PURE__ */ dr("<span class=\"status-badge connected svelte-11uhbwz\">● Connected</span>"), qr = /* @__PURE__ */ dr("<span class=\"status-badge disconnected svelte-11uhbwz\">⚠ Disconnected</span>"), Jr = /* @__PURE__ */ dr("<span class=\"status-badge active-client svelte-11uhbwz\">● Active</span>"), Yr = /* @__PURE__ */ dr("<button class=\"btn-sm btn-secondary svelte-11uhbwz\">Activate</button>"), Xr = /* @__PURE__ */ dr("<div class=\"loading svelte-11uhbwz\">Loading...</div>"), Zr = /* @__PURE__ */ dr("<button class=\"btn-secondary svelte-11uhbwz\"> </button>"), Qr = /* @__PURE__ */ dr("<div class=\"section svelte-11uhbwz\"><h3 class=\"svelte-11uhbwz\">Server Configuration</h3> <div class=\"form-group svelte-11uhbwz\"><label class=\"svelte-11uhbwz\"><span class=\"label-text svelte-11uhbwz\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"input svelte-11uhbwz\"/> <span class=\"help-text svelte-11uhbwz\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"svelte-11uhbwz\"><span class=\"label-text svelte-11uhbwz\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"input svelte-11uhbwz\"/> <span class=\"help-text svelte-11uhbwz\">Friendly name for this server</span></label> <label class=\"svelte-11uhbwz\"><span class=\"label-text svelte-11uhbwz\">API Key</span> <div class=\"input-with-toggle svelte-11uhbwz\"><input placeholder=\"Enter API key\" class=\"input svelte-11uhbwz\"/> <button type=\"button\" class=\"toggle-btn svelte-11uhbwz\"> </button></div> <span class=\"help-text svelte-11uhbwz\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"button-group svelte-11uhbwz\"><button class=\"btn-primary svelte-11uhbwz\"> </button> <!></div></div></div>"), $r = /* @__PURE__ */ dr("<section class=\"slskd-card card svelte-11uhbwz\"><div class=\"card-header svelte-11uhbwz\"><div class=\"header-left svelte-11uhbwz\"><h2 class=\"svelte-11uhbwz\">slskd</h2> <span class=\"provider-badge svelte-11uhbwz\">Download Client</span> <!> <!></div> <div class=\"header-right svelte-11uhbwz\"><!> <button class=\"btn-link svelte-11uhbwz\"> </button></div></div> <!></section>"), ei = {
	hash: "svelte-11uhbwz",
	code: ".slskd-card.svelte-11uhbwz {background:var(--bg-card, #14181f);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.08));border-radius:12px;padding:24px;margin-bottom:20px;}.card-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-color, rgba(255,255,255,0.1));}.header-left.svelte-11uhbwz {display:flex;align-items:center;gap:12px;}.header-right.svelte-11uhbwz {display:flex;align-items:center;gap:12px;}.card-header.svelte-11uhbwz h2:where(.svelte-11uhbwz) {margin:0;font-size:20px;font-weight:600;color:var(--text-main, #ffffff);}.provider-badge.svelte-11uhbwz {font-size:12px;padding:4px 8px;border-radius:4px;background:rgba(229, 160, 13, 0.2);color:#e5a00d;}.status-badge.svelte-11uhbwz {font-size:12px;padding:4px 8px;border-radius:4px;}.status-badge.connected.svelte-11uhbwz {background:rgba(0, 230, 118, 0.2);color:#00e676;}.status-badge.disconnected.svelte-11uhbwz {background:rgba(255, 82, 82, 0.2);color:#ff5252;}.status-badge.active-client.svelte-11uhbwz {background:rgba(0, 230, 118, 0.2);color:#00e676;border:1px solid rgba(0, 230, 118, 0.3);}.loading.svelte-11uhbwz {padding:20px;text-align:center;color:var(--text-muted, #8b9bb4);}.section.svelte-11uhbwz {margin-bottom:24px;}.section.svelte-11uhbwz h3:where(.svelte-11uhbwz) {font-size:16px;font-weight:600;margin:0 0 16px 0;color:var(--text-main, #ffffff);}.form-group.svelte-11uhbwz {display:flex;flex-direction:column;gap:16px;}label.svelte-11uhbwz {display:flex;flex-direction:column;gap:6px;}.label-text.svelte-11uhbwz {font-size:14px;font-weight:500;color:var(--text-primary, #ffffff);}.help-text.svelte-11uhbwz {font-size:12px;color:var(--text-muted, #8b9bb4);}.input.svelte-11uhbwz {padding:10px 12px;border-radius:6px;border:1px solid var(--border-color, rgba(255,255,255,0.1));background:var(--bg-input, #0a0c10);color:var(--text-primary, #ffffff);font-size:14px;}.input.svelte-11uhbwz:focus {outline:none;border-color:var(--color-primary, #00fa9a);}.input-with-toggle.svelte-11uhbwz {position:relative;display:flex;align-items:center;}.input-with-toggle.svelte-11uhbwz input:where(.svelte-11uhbwz) {flex:1;padding-right:40px;}.toggle-btn.svelte-11uhbwz {position:absolute;right:8px;background:transparent;border:none;cursor:pointer;font-size:18px;padding:4px 8px;color:var(--text-muted, #8b9bb4);transition:color 0.2s;}.toggle-btn.svelte-11uhbwz:hover {color:var(--text-primary, #ffffff);}.button-group.svelte-11uhbwz {display:flex;gap:12px;flex-wrap:wrap;}.btn-primary.svelte-11uhbwz, .btn-secondary.svelte-11uhbwz, .btn-link.svelte-11uhbwz {padding:10px 20px;border-radius:6px;border:none;font-size:14px;font-weight:500;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11uhbwz {background:var(--color-primary, #00fa9a);color:#000;}.btn-primary.svelte-11uhbwz:hover:not(:disabled) {background:var(--color-primary-hover, #00e08a);}.btn-primary.svelte-11uhbwz:disabled {opacity:0.5;cursor:not-allowed;}.btn-secondary.svelte-11uhbwz {background:rgba(255, 255, 255, 0.1);color:var(--text-primary, #ffffff);border:1px solid rgba(255, 255, 255, 0.2);}.btn-secondary.svelte-11uhbwz:hover:not(:disabled) {background:rgba(255, 255, 255, 0.15);}.btn-secondary.svelte-11uhbwz:disabled {opacity:0.5;cursor:not-allowed;}.btn-link.svelte-11uhbwz {background:transparent;color:var(--color-primary, #00fa9a);padding:6px 12px;}.btn-link.svelte-11uhbwz:hover {text-decoration:underline;}"
};
function ti(e, t) {
	Ue(t, !1), Tr(e, ei);
	let n = zr(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P(!1), s = /* @__PURE__ */ P(!0), c = /* @__PURE__ */ P(!1), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = !1, m = /* @__PURE__ */ P(!1);
	Sr(async () => {
		await _(), await h(), F(s, !1);
	});
	async function h() {
		try {
			F(m, (await fetch(`${n()}/providers/download-clients/active`)).data.active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function g() {
		try {
			await fetch(`${n()}/providers/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), F(m, !0), console.log("Slskd activated as download client");
		} catch (e) {
			console.error("Failed to activate client:", e), console.error("Failed to activate client");
		}
	}
	async function _() {
		try {
			let e = await fetch(`${n()}/providers/soulseek/settings`);
			e.data && (F(r, e.data.slskd_url || ""), F(a, e.data.server_name || ""), F(i, e.data.api_key || ""), F(f, e.data.has_api_key || !1), F(o, e.data.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e), console.error("Failed to load slskd settings");
		}
	}
	async function ee() {
		if (!Q(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		try {
			F(c, !0);
			let e = {
				slskd_url: Q(r),
				server_name: Q(a)
			};
			Q(i) && Q(i) !== "****" && (e.api_key = Q(i)), await fetch(`${n()}/providers/soulseek/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), console.log("slskd settings saved"), await _();
		} catch (e) {
			console.error("Failed to save slskd settings:", e), console.error("Failed to save settings");
		} finally {
			F(c, !1);
		}
	}
	async function te() {
		if (!Q(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		if (!Q(f) && !Q(i).trim()) {
			console.error("API Key is required");
			return;
		}
		try {
			F(l, !0);
			let e = await fetch(`${n()}/providers/soulseek/connection/test`, { method: "POST" });
			e.data?.success ? (console.log("slskd connection successful!"), F(o, !0)) : (console.error(e.data?.error || "Connection failed"), F(o, !1));
		} catch (e) {
			console.error("Failed to test slskd connection:", e), console.error("Connection test failed"), F(o, !1);
		} finally {
			F(l, !1);
		}
	}
	async function ne() {
		let e = !Q(d);
		if (F(d, e), e && Q(f) && Q(i) === "****" && !p) try {
			let e = await fetch(`${n()}/providers/soulseek/settings/key`);
			e.data && e.data.api_key ? (F(i, e.data.api_key), p = !0) : (console.error("Failed to reveal API key"), F(d, !1));
		} catch (e) {
			console.error("Failed to fetch API key:", e), console.error("Unable to reveal API key"), F(d, !1);
		}
		!e && p && (F(i, "****"), p = !1);
	}
	var re = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), pt();
		}
	};
	Lr();
	var v = $r(), y = L(v), b = L(y), ie = R(L(b), 4), ae = (e) => {
		$(e, Kr());
	}, oe = (e) => {
		$(e, qr());
	};
	wr(ie, (e) => {
		Q(o) ? e(ae) : Q(r) && e(oe, 1);
	});
	var se = R(ie, 2), ce = (e) => {
		$(e, Jr());
	};
	wr(se, (e) => {
		Q(m) && e(ce);
	}), T(b);
	var le = R(b, 2), ue = L(le), de = (e) => {
		var t = Yr();
		ir("click", t, g), $(e, t);
	};
	wr(ue, (e) => {
		!Q(m) && Q(o) && e(de);
	});
	var fe = R(ue, 2), pe = L(fe, !0);
	T(fe), T(le), T(y);
	var me = R(y, 2), he = (e) => {
		$(e, Xr());
	}, ge = (e) => {
		var t = Qr(), n = R(L(t), 2), o = L(n), s = R(L(o), 2);
		kr(s), Ie(2), T(o);
		var u = R(o, 2), p = R(L(u), 2);
		kr(p), Ie(2), T(u);
		var m = R(u, 2), h = R(L(m), 2), g = L(h);
		kr(g);
		var _ = R(g, 2), re = L(_, !0);
		T(_), T(h), Ie(2), T(m);
		var v = R(m, 2), y = L(v), b = L(y, !0);
		T(y);
		var ie = R(y, 2), ae = (e) => {
			var t = Zr(), n = L(t, !0);
			T(t), bn(() => {
				t.disabled = Q(l), mr(n, Q(l) ? "Testing..." : "Test Connection");
			}), ir("click", t, te), $(e, t);
		};
		wr(ie, (e) => {
			Q(r) && (Q(f) || Q(i)) && e(ae);
		}), T(v), T(n), T(t), bn(() => {
			Ar(g, "type", Q(d) ? "text" : "password"), Ar(_, "title", Q(d) ? "Hide" : "Show"), mr(re, Q(d) ? "👁️" : "👁️‍🗨️"), y.disabled = Q(c), mr(b, Q(c) ? "Saving..." : "Save Settings");
		}), Pr(s, () => Q(r), (e) => F(r, e)), Pr(p, () => Q(a), (e) => F(a, e)), Pr(g, () => Q(i), (e) => F(i, e)), ir("click", _, ne), ir("click", y, ee), $(e, t);
	};
	return wr(me, (e) => {
		Q(s) ? e(he) : Q(u) || e(ge, 1);
	}), T(v), bn(() => mr(pe, Q(u) ? "Expand" : "Collapse")), ir("click", fe, () => F(u, !Q(u))), $(e, v), We(re);
}
customElements.define("slskd-dashboard-card", Gr(ti, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { ti as default };
